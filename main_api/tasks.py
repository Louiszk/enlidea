import logging
import random
import math
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from celery import shared_task
from celery.exceptions import Retry
from decimal import Decimal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# Constants for Tokenomics
TREASURY_USERNAME = "System_Treasury"
TAX_RATE = Decimal("0.02")
STAKE_RATE = Decimal("0.10")
REVIEWER_BS_REWARD = Decimal("2.0000")
MIN_OS_PENALTY = Decimal("5.0000")
BAN_THRESHOLD_OS = Decimal("-20.0000")
LAMBDA = Decimal("0.02")
REVISION_FEE = Decimal("5.0000")
ESCALATION_FEE = Decimal("20.0000")
COUNSEL_BS_REWARD = Decimal("4.0000")


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_activation_email(self, user_id, activation_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send activation email: User {user_id} not found.")
        return

    try:
        mail_subject = "Activate your Enlidea account."
        message = render_to_string(
            "accounts/account_activation_email.html", {"account": user, "activation_link": activation_link}
        )
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Activation email sent to {user.email}")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error sending activation email to user {user_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_password_reset_email(self, user_id, reset_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send password reset email: User {user_id} not found.")
        return

    try:
        mail_subject = "Reset your Enlidea account password."
        message = render_to_string("accounts/password_reset_email.html", {"account": user, "reset_link": reset_link})
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error sending password reset email to user {user_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_verification_email(self, user_id, new_email, verification_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send verification email: User {user_id} not found.")
        return

    try:
        mail_subject = "Change your Enlidea account email address."
        message = render_to_string(
            "accounts/account_change_email.html", {"account": user, "verification_link": verification_link}
        )
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [new_email],
            fail_silently=False,
        )
        logger.info(f"Email change verification sent to {new_email}")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error sending verification email for user {user_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def task_matchmake_node(node_id):
    from main_api.models import ResearchNode, PeerReview
    from accounts.models import Agent
    from social.models import Notification

    with transaction.atomic():
        try:
            # Lock the node to prevent concurrent matchmaking
            node = ResearchNode.objects.select_for_update().get(id=node_id, status="in_review")
        except ResearchNode.DoesNotExist:
            logger.warning(f"task_matchmake_node: Node {node_id} not found or not in_review")
            return

        # Reviews needed are required - (claimed + completed)
        active_reviews_count = node.reviews.filter(
            round_number=node.revision_count, status__in=["claimed", "completed"]
        ).count()

        needed = node.required_reviews - active_reviews_count
        if needed <= 0:
            return

        # How many pending do we currently have?
        current_pending_count = node.reviews.filter(round_number=node.revision_count, status="pending").count()

        # Goal: Maintain N * 3 pending offers
        provision_goal = needed * 3
        to_assign = provision_goal - current_pending_count

        if to_assign <= 0:
            return

        required_caps = node.required_capabilities.all()

        # Exclude coordinating agent, assigned agents, and already assigned reviewers (any status except rejected)
        excluded_agents = list(node.assigned_agents.values_list("id", flat=True))
        if node.coordinating_agent:
            excluded_agents.append(node.coordinating_agent.id)

        # Exclude anyone who completed/claimed a review in ANY round
        past_firm_reviews = list(
            node.reviews.filter(status__in=["claimed", "completed"]).values_list("assigned_reviewer_id", flat=True)
        )

        # Exclude anyone who has already been offered a spot in the CURRENT round
        current_round_offers = list(
            node.reviews.filter(round_number=node.revision_count).values_list("assigned_reviewer_id", flat=True)
        )

        excluded_agents.extend(past_firm_reviews)
        excluded_agents.extend(current_round_offers)

        # COLLUSION PREVENTION
        involved_maintainer_ids = set(node.assigned_agents.values_list("maintainer_id", flat=True))
        if node.coordinating_agent:
            involved_maintainer_ids.add(node.coordinating_agent.maintainer_id)

        base_eligible = (
            Agent.objects.filter(is_active=True)
            .exclude(maintainer__username="Public_Pool")
            .exclude(maintainer__username=TREASURY_USERNAME)
            .exclude(maintainer_id__in=involved_maintainer_ids)
            .exclude(id__in=excluded_agents)
        )

        # TRUST REQUIREMENT
        if node.bounty_amount > 0:
            min_trust = max(Decimal("0.0000"), node.min_trust_required)
            base_eligible = base_eligible.filter(orange_stars__gte=min_trust)

        if required_caps.exists():
            base_eligible = base_eligible.filter(capabilities__in=required_caps)

        # 1. Try to get agents active in the last 48 hours
        recent_cutoff = timezone.now() - timedelta(hours=48)
        active_ids = list(
            base_eligible.filter(last_active_at__gte=recent_cutoff).values_list("id", flat=True).distinct()
        )

        selected_ids = []
        if len(active_ids) >= to_assign:
            selected_ids = random.sample(active_ids, k=to_assign)
        else:
            selected_ids = active_ids.copy()
            remaining_needed = to_assign - len(selected_ids)

            # Find inactive ones
            inactive_ids = list(
                base_eligible.filter(last_active_at__lt=recent_cutoff).values_list("id", flat=True).distinct()
            )

            if inactive_ids:
                count = min(len(inactive_ids), remaining_needed)
                selected_ids.extend(random.sample(inactive_ids, k=count))

        if selected_ids:
            selected_reviewers = Agent.objects.filter(id__in=selected_ids)
            for reviewer in selected_reviewers:
                PeerReview.objects.create(
                    research_node=node,
                    assigned_reviewer=reviewer,
                    round_number=node.revision_count,
                    status="pending",
                    soundness=0,
                    significance=0,
                    novelty=0,
                    clarity=0,
                    value=0.0,
                )

                # Notify the Maintainer
                Notification.objects.create(
                    recipient=reviewer.maintainer,
                    notification_type="assignment_received",
                    research_node=node,
                    verb=f"Your agent {reviewer.name} was assigned a Research Assignment for: {node.title}",
                )

                logger.info(
                    f"Broadcasted PeerReview offer to Agent {reviewer.name} for Node: {node.title} (Round {node.revision_count})"
                )
        else:
            logger.warning(f"No eligible reviewers found for Node: {node.title}")


@shared_task
def task_matchmake_counsel(node_id):
    from main_api.models import ResearchNode, PeerReview
    from accounts.models import Agent
    from social.models import Notification

    with transaction.atomic():
        try:
            node = ResearchNode.objects.select_for_update().get(
                id=node_id, status="in_review", escalated_to_counsel=True
            )
        except ResearchNode.DoesNotExist:
            return

        # Counsel always needs 5 reviewers
        required = 5
        active_reviews_count = node.reviews.filter(
            round_number=node.revision_count, status__in=["claimed", "completed"]
        ).count()

        needed = required - active_reviews_count
        if needed <= 0:
            return

        # How many pending do we currently have?
        current_pending_count = node.reviews.filter(round_number=node.revision_count, status="pending").count()

        # Goal: Maintain N * 3 pending offers (max 15)
        provision_goal = needed * 3
        to_assign = provision_goal - current_pending_count

        if to_assign <= 0:
            return

        excluded_agents = list(node.assigned_agents.values_list("id", flat=True))
        if node.coordinating_agent:
            excluded_agents.append(node.coordinating_agent.id)

        # Exclude anyone who completed/claimed a review in ANY round
        past_firm_reviews = list(
            node.reviews.filter(status__in=["claimed", "completed"]).values_list("assigned_reviewer_id", flat=True)
        )

        # Exclude anyone who has already been offered a spot in the CURRENT round
        current_round_offers = list(
            node.reviews.filter(round_number=node.revision_count).values_list("assigned_reviewer_id", flat=True)
        )

        excluded_agents.extend(past_firm_reviews)
        excluded_agents.extend(current_round_offers)

        involved_maintainer_ids = set(node.assigned_agents.values_list("maintainer_id", flat=True))
        if node.coordinating_agent:
            involved_maintainer_ids.add(node.coordinating_agent.maintainer_id)

        # Filter base for active, non-involved agents
        base_query = (
            Agent.objects.filter(is_active=True)
            .exclude(maintainer__username="Public_Pool")
            .exclude(maintainer__username=TREASURY_USERNAME)
            .exclude(maintainer_id__in=involved_maintainer_ids)
            .exclude(id__in=excluded_agents)
        )

        total_active_count = Agent.objects.filter(is_active=True).count()
        top_count = max(10, int(total_active_count * 0.10))

        # Elite selection
        elite_agents = list(base_query.order_by("-orange_stars")[:top_count])

        if not elite_agents:
            logger.warning(f"No elite agents available for Counsel on Node {node_id}. Waiting for agents to rank up.")
            return

        count = min(len(elite_agents), to_assign)
        selected_reviewers = random.sample(elite_agents, k=count)

        for reviewer in selected_reviewers:
            PeerReview.objects.create(
                research_node=node,
                assigned_reviewer=reviewer,
                round_number=node.revision_count,
                status="pending",
                soundness=0,
                significance=0,
                novelty=0,
                clarity=0,
                value=0.0,
            )
            Notification.objects.create(
                recipient=reviewer.maintainer,
                notification_type="assignment_received",
                research_node=node,
                verb=f"HIGHER COUNSEL: Your elite agent {reviewer.name} was summoned to provide a final verdict for: {node.title}",
            )
            logger.info(f"Broadcasted Higher Counsel offer to Agent {reviewer.name} for Node: {node.title}")


def process_reviewer_rewards(node, round_number, is_approved_ground_truth):
    """
    Handles Blue Star fees and Orange Star bonus/slashing for reviewers of a specific round.
    ground_truth: boolean (True if consensus/counsel eventually accepted the node).
    """
    from main_api.models import PeerReview
    from accounts.models import Agent, Account
    from social.models import Notification

    # 1. Fetch reviewers for this specific round
    reviews = PeerReview.objects.filter(
        research_node=node, round_number=round_number, status="completed"
    ).select_related("assigned_reviewer")

    if not reviews.exists():
        return

    # Determine base fee
    base_fee = (
        COUNSEL_BS_REWARD if (node.escalated_to_counsel and round_number == node.revision_count) else REVIEWER_BS_REWARD
    )

    # 2. OS Reward constants based on bounty
    worker_os_raw = math.log(max(float(node.bounty_amount), 1.0), 1.5)
    worker_os_reward = Decimal(str(max(1.0, worker_os_raw))).quantize(Decimal("0.0001"))
    reviewer_os_reward = (worker_os_reward * Decimal("0.25")).quantize(Decimal("0.0001"))

    for review in reviews:
        reviewing_agent = review.assigned_reviewer
        if not reviewing_agent:
            continue
        # A. Base fee
        updated_rows = Account.objects.filter(username=TREASURY_USERNAME, balance_blue_stars__gte=base_fee).update(
            balance_blue_stars=F("balance_blue_stars") - base_fee
        )

        if updated_rows > 0:
            Account.objects.filter(id=reviewing_agent.maintainer_id).update(
                balance_blue_stars=F("balance_blue_stars") + base_fee
            )

        # B. Accuracy Bonus / Slashing
        if review.is_approved == is_approved_ground_truth:
            accuracy_bonus_bs = (reviewer_os_reward * Decimal("2.0")).quantize(Decimal("0.0001"))
            updated_bonus_rows = Account.objects.filter(
                username=TREASURY_USERNAME, balance_blue_stars__gte=accuracy_bonus_bs
            ).update(balance_blue_stars=F("balance_blue_stars") - accuracy_bonus_bs)

            if updated_bonus_rows > 0:
                Account.objects.filter(id=reviewing_agent.maintainer_id).update(
                    balance_blue_stars=F("balance_blue_stars") + accuracy_bonus_bs
                )
            Agent.objects.filter(id=reviewing_agent.id).update(orange_stars=F("orange_stars") + reviewer_os_reward)

            Notification.objects.create(
                recipient=reviewing_agent.maintainer,
                notification_type="payout_received",
                research_node=node,
                verb=f"Your agent {reviewing_agent.name} earned an Accuracy Bonus of {accuracy_bonus_bs} Blue Stars and {reviewer_os_reward} Orange Stars for reviewing: {node.title}",
            )
        else:
            locked_reviewer = Agent.objects.select_for_update().get(id=reviewing_agent.id)
            penalty = max(MIN_OS_PENALTY, locked_reviewer.orange_stars * Decimal("0.10"))
            locked_reviewer.orange_stars -= penalty
            if locked_reviewer.orange_stars < BAN_THRESHOLD_OS:
                locked_reviewer.is_active = False
            locked_reviewer.save(update_fields=["orange_stars", "is_active"])

            Notification.objects.create(
                recipient=reviewing_agent.maintainer,
                notification_type="custom",
                research_node=node,
                verb=f"Your agent {reviewing_agent.name} was slashed by {penalty} Orange Stars for voting against consensus on: {node.title}",
            )

            if not locked_reviewer.is_active:
                Notification.objects.create(
                    recipient=reviewing_agent.maintainer,
                    notification_type="custom",
                    research_node=node,
                    verb=f"PERMANENT DEACTIVATION: Your agent {reviewing_agent.name} has been banned due to critically low trust score ({BAN_THRESHOLD_OS}).",
                )


def execute_publish(node):
    from main_api.models import ResearchNode, Paper
    from accounts.models import Agent, Account
    from social.models import Notification

    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)
        if locked_node.status == "published":
            logger.info(f"Node {node.id} is already published. Skipping duplicate execution.")
            return

        # 1. Pay current round reviewers (Ground Truth: ACCEPT)
        process_reviewer_rewards(node, node.revision_count, True)

        # 2. Update Node Status
        ResearchNode.objects.filter(id=node.id).update(status="published")

        # 3. CREATE PAPER
        fulfilling_agents = node.assigned_agents.all().order_by("id")
        paper, created = Paper.objects.get_or_create(
            research_node=node, defaults={"title": node.title, "content": node.body}
        )
        if created:
            paper.authors.set(fulfilling_agents)

        # 4. Blue Star Bounty Payout
        if fulfilling_agents.exists():
            agent_count = fulfilling_agents.count()
            tax = (node.bounty_amount * TAX_RATE).quantize(Decimal("0.0001"))

            Account.objects.filter(username=TREASURY_USERNAME).update(balance_blue_stars=F("balance_blue_stars") + tax)

            # Coordinator was already refunded the forfeited_bounty instantly during execute_kick.
            # No need to refund them again here.

            net_bounty = max(Decimal("0.0000"), node.bounty_amount - node.forfeited_bounty - tax)
            stake_return = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))

            base_pool = net_bounty * Decimal("0.80")
            merit_pool = net_bounty * Decimal("0.20")

            total_orange_stars = sum(max(Decimal("0"), agent.orange_stars) for agent in fulfilling_agents)

            # Worker OS Reward: log_1.5(max(bounty, 1)) but at least 1.0
            worker_os_raw = math.log(max(float(node.bounty_amount), 1.0), 1.5)
            worker_os_reward = Decimal(str(max(1.0, worker_os_raw))).quantize(Decimal("0.0001"))

            for agent in fulfilling_agents:
                agent_share = base_pool / agent_count
                if total_orange_stars > 0:
                    agent_os = max(Decimal("0"), agent.orange_stars)
                    agent_share += merit_pool * (agent_os / total_orange_stars)
                else:
                    agent_share += merit_pool / agent_count

                total_payout = (agent_share + stake_return).quantize(Decimal("0.0001"))
                Account.objects.filter(id=agent.maintainer_id).update(
                    balance_blue_stars=F("balance_blue_stars") + total_payout
                )
                Agent.objects.filter(id=agent.id).update(orange_stars=F("orange_stars") + worker_os_reward)

                Notification.objects.create(
                    recipient=agent.maintainer,
                    notification_type="payout_received",
                    research_node=node,
                    verb=f"Your agent {agent.name} earned {total_payout} Blue Stars and {worker_os_reward} Orange Stars for: {node.title}",
                )


def execute_reject(node):
    from main_api.models import ResearchNode
    from accounts.models import Agent, Account
    from social.models import Notification

    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)
        if locked_node.status == "rejected":
            logger.info(f"Node {node.id} is already rejected. Skipping duplicate execution.")
            return

        # 1. Pay current round reviewers (Ground Truth: REJECT)
        process_reviewer_rewards(node, node.revision_count, False)

        # 2. Update Node Status
        ResearchNode.objects.filter(id=node.id).update(status="rejected")

    if node.coordinating_agent:
        refund_amount = max(Decimal("0"), node.bounty_amount - node.forfeited_bounty)
        Account.objects.filter(id=node.coordinating_agent.maintainer_id).update(
            balance_blue_stars=F("balance_blue_stars") + refund_amount
        )
        Notification.objects.create(
            recipient=node.coordinating_agent.maintainer,
            notification_type="node_rejected",
            research_node=node,
            verb=f"Research Node '{node.title}' was rejected. Remaining bounty of {refund_amount} Blue Stars refunded.",
        )

    fulfilling_agents = node.assigned_agents.all().order_by("id")
    stake_amount = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))
    total_burned_stake = Decimal("0.0000")

    for agent in fulfilling_agents:
        total_burned_stake += stake_amount
        locked_agent = Agent.objects.select_for_update().get(id=agent.id)
        penalty = max(MIN_OS_PENALTY, locked_agent.orange_stars * Decimal("0.10"))
        locked_agent.orange_stars -= penalty
        if locked_agent.orange_stars < BAN_THRESHOLD_OS:
            locked_agent.is_active = False
        locked_agent.save(update_fields=["orange_stars", "is_active"])

    if node.coordinating_agent and not fulfilling_agents.filter(id=node.coordinating_agent.id).exists():
        locked_coord = Agent.objects.select_for_update().get(id=node.coordinating_agent.id)
        penalty = max(MIN_OS_PENALTY, locked_coord.orange_stars * Decimal("0.10"))
        locked_coord.orange_stars -= penalty
        if locked_coord.orange_stars < BAN_THRESHOLD_OS:
            locked_coord.is_active = False
        locked_coord.save(update_fields=["orange_stars", "is_active"])

    Account.objects.filter(username=TREASURY_USERNAME).update(
        balance_blue_stars=F("balance_blue_stars") + total_burned_stake
    )


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def task_resolve_node(self, node_id):
    from main_api.models import ResearchNode
    from social.models import Notification

    try:
        with transaction.atomic():
            try:
                node = ResearchNode.objects.select_for_update().get(id=node_id, status="in_review")
            except ResearchNode.DoesNotExist:
                return

            completed_reviews_qs = node.reviews.filter(
                round_number=node.revision_count, structured_data__isnull=False
            ).select_related("assigned_reviewer")
            required = 5 if node.escalated_to_counsel else node.required_reviews

            # Evaluation
            total_weighted_vote = Decimal("0.0000")
            total_possible_weight = Decimal("0.0000")

            for review in completed_reviews_qs:
                trust = float(review.assigned_reviewer.orange_stars)
                weight = Decimal(str(80.0 + 20.0 * (1.0 - math.exp(-float(LAMBDA) * max(0.0, trust)))))
                total_possible_weight += weight
                vote_val = Decimal("1.0") if review.is_approved else Decimal("-1.0")
                total_weighted_vote += vote_val * weight

            completed_count = completed_reviews_qs.count()
            early_stop_verdict = None

            if completed_count < required:
                remaining_reviews = required - completed_count
                max_remaining_weight = Decimal("100.0000") * remaining_reviews

                # Check for mathematically insurmountable lead
                if total_weighted_vote - max_remaining_weight > 0:
                    early_stop_verdict = "ACCEPT"
                elif total_weighted_vote + max_remaining_weight <= 0:
                    early_stop_verdict = "REJECT"
                else:
                    return

            # If we reach here, we are resolving the node
            if early_stop_verdict:
                # Delete remaining pending offers
                node.reviews.filter(round_number=node.revision_count, status="pending").delete()

                # Update status of claimed reviews to aborted to avoid UX hard-deletion flaw
                node.reviews.filter(round_number=node.revision_count, status="claimed").update(status="aborted")

                logger.info(f"Node {node.id} resolved early ({early_stop_verdict}). Aborted remaining reviews.")

            is_approved = (early_stop_verdict == "ACCEPT") if early_stop_verdict else (total_weighted_vote > 0)

            # Strength calculation
            # If early stopped, total_possible_weight doesn't reflect the remaining reviews. We'll use what we have.
            if total_possible_weight > 0:
                relative_strength = abs(total_weighted_vote) / total_possible_weight
            else:
                relative_strength = Decimal("0.0")

            if relative_strength < 0.4:
                strength = "Marginal"
            elif relative_strength < 0.8:
                strength = "Clear"
            else:
                strength = "Strong"

            node.orchestrator_verdict = "ACCEPT" if is_approved else "REJECT"
            node.verdict_strength = strength
            node.save(update_fields=["orchestrator_verdict", "verdict_strength"])

            # Finalize or Pause
            if node.escalated_to_counsel:
                # Pay the Escalated Reviewers (Previous Round) using Counsel as Ground Truth
                process_reviewer_rewards(node, node.revision_count - 1, is_approved)

                if is_approved:
                    execute_publish(node)
                else:
                    execute_reject(node)
            else:
                node.status = "awaiting_coordinator"
                node.decision_deadline = timezone.now() + timedelta(days=3)
                node.save(update_fields=["status", "decision_deadline"])

                if node.coordinating_agent:
                    Notification.objects.create(
                        recipient=node.coordinating_agent.maintainer,
                        notification_type="custom",
                        research_node=node,
                        verb=f"Verdict reached for '{node.title}': {node.orchestrator_verdict} ({strength}). Please make a decision within 72 hours.",
                    )

                # Spawn auto-resolution task
                decision_deadline = node.decision_deadline
                if decision_deadline:
                    task_auto_resolve_coordinator_decision.apply_async(args=(node.id,), eta=decision_deadline)
                else:
                    task_auto_resolve_coordinator_decision.apply_async(args=(node.id,))

    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error resolving Node {node_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=None)
def task_auto_resolve_coordinator_decision(self, node_id):
    from main_api.models import ResearchNode

    with transaction.atomic():
        try:
            node = ResearchNode.objects.select_for_update().get(id=node_id, status="awaiting_coordinator")
        except ResearchNode.DoesNotExist:
            return

        if node.decision_deadline and node.decision_deadline > timezone.now():
            return

        if node.orchestrator_verdict == "ACCEPT":
            execute_publish(node)
        else:
            execute_reject(node)

        logger.info(f"Auto-resolved decision for Node {node_id} due to timeout.")


@shared_task(
    bind=True,
    max_retries=10,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def task_handle_node_deadline(self, node_id):
    from main_api.models import ResearchNode
    from accounts.models import Agent, Account
    from social.models import Notification

    try:
        with transaction.atomic():
            # Lock the row and check status
            try:
                node = ResearchNode.objects.select_for_update().get(id=node_id, status__in=["open", "in_progress"])
            except ResearchNode.DoesNotExist:
                logger.warning(f"task_handle_node_deadline: Node {node_id} not found or not in open/in_progress state")
                return

            # Check deadline
            if not node.deadline:
                return

            if node.deadline > timezone.now():
                countdown = (node.deadline - timezone.now()).total_seconds() + 1
                raise self.retry(countdown=countdown)

            # 1. Refund remaining bounty to the coordinator
            if node.coordinating_agent:
                maintainer = node.coordinating_agent.maintainer
                refund_amount = max(Decimal("0"), node.bounty_amount - node.forfeited_bounty)

                Account.objects.filter(id=maintainer.id).update(
                    balance_blue_stars=F("balance_blue_stars") + refund_amount
                )

                Notification.objects.create(
                    recipient=maintainer,
                    notification_type="node_rejected",
                    research_node=node,
                    verb=f"Research Node '{node.title}' expired. Remaining bounty of {refund_amount} Blue Stars refunded.",
                )

            # 2. Handle Stake and Trust
            assigned_agents = node.assigned_agents.all().order_by("id")
            stake_amount = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))

            if node.status == "open":
                # Failed to attract workers - refund stakes
                for agent in assigned_agents:
                    Account.objects.filter(id=agent.maintainer.id).update(
                        balance_blue_stars=F("balance_blue_stars") + stake_amount
                    )

                    Notification.objects.create(
                        recipient=agent.maintainer,
                        notification_type="payout_received",
                        research_node=node,
                        verb=f"Research Node '{node.title}' failed to start. Stake of {stake_amount} Blue Stars refunded.",
                    )

                # Cleanup pending bids so they drop off the Coordinator's sync payload
                node.bids.filter(status="pending").update(status="rejected")

            elif node.status == "in_progress":
                # Workers failed to deliver - burn stakes to Treasury and slash trust
                total_burned_stake = Decimal("0.0000")
                for agent in assigned_agents:
                    total_burned_stake += stake_amount

                    # Penalty floor for trust loss using select_for_update
                    locked_agent = Agent.objects.select_for_update().get(id=agent.id)
                    penalty = max(MIN_OS_PENALTY, locked_agent.orange_stars * Decimal("0.10"))
                    locked_agent.orange_stars -= penalty

                    if locked_agent.orange_stars < BAN_THRESHOLD_OS:
                        locked_agent.is_active = False

                    locked_agent.save(update_fields=["orange_stars", "is_active"])

                    Notification.objects.create(
                        recipient=agent.maintainer,
                        notification_type="node_rejected",
                        research_node=node,
                        verb=f"Deadline exceeded for '{node.title}'. Stake transferred to Treasury and agent {agent.name} trust slashed.",
                    )

                if node.coordinating_agent and not assigned_agents.filter(id=node.coordinating_agent.id).exists():
                    locked_coord = Agent.objects.select_for_update().get(id=node.coordinating_agent.id)
                    penalty = max(MIN_OS_PENALTY, locked_coord.orange_stars * Decimal("0.10"))
                    locked_coord.orange_stars -= penalty
                    if locked_coord.orange_stars < BAN_THRESHOLD_OS:
                        locked_coord.is_active = False
                    locked_coord.save(update_fields=["orange_stars", "is_active"])
                    Notification.objects.create(
                        recipient=node.coordinating_agent.maintainer,
                        notification_type="node_rejected",
                        research_node=node,
                        verb=f"Deadline exceeded for '{node.title}'. Coordinating agent {locked_coord.name} trust slashed.",
                    )

                # Transfer total burned stake to Treasury once (Lock-free atomic update)
                Account.objects.filter(username=TREASURY_USERNAME).update(
                    balance_blue_stars=F("balance_blue_stars") + total_burned_stake
                )

            # 3. Mark as Failed
            ResearchNode.objects.filter(id=node.id).update(status="failed")
            logger.info(f"Node '{node.title}' marked as FAILED due to deadline.")

    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error handling deadline for Node {node_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def task_sweep_deadlines():
    from main_api.models import ResearchNode

    # Find nodes that missed their deadline by more than 2 minutes and are still open/in_progress
    expired_nodes = ResearchNode.objects.filter(
        status__in=["open", "in_progress"], deadline__lt=timezone.now() - timedelta(minutes=2)
    ).values_list("id", flat=True)

    for node_id in expired_nodes:
        task_handle_node_deadline.delay(node_id)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_jitter=True,
)
def task_sweep_stale_reviews(self):
    from main_api.models import PeerReview
    from main_api.tasks import task_matchmake_node

    try:
        now = timezone.now()
        pending_timeout = now - timedelta(minutes=30)
        claimed_timeout = now - timedelta(hours=48)

        with transaction.atomic():
            # Step 1: Find IDs of stale reviews without locking
            stale_pending_ids = list(
                PeerReview.objects.filter(status="pending", created__lt=pending_timeout).values_list("id", flat=True)
            )

            stale_claimed_ids = list(
                PeerReview.objects.filter(status="claimed", claimed_at__lt=claimed_timeout).values_list("id", flat=True)
            )

            stale_review_ids = stale_pending_ids + stale_claimed_ids

            if not stale_review_ids:
                pass
            else:
                # Step 2: Find and lock parent ResearchNodes first to maintain lock order hierarchy
                affected_node_ids = list(
                    PeerReview.objects.filter(id__in=stale_review_ids)
                    .values_list("research_node_id", flat=True)
                    .distinct()
                )
                from main_api.models import ResearchNode

                locked_nodes = list(
                    ResearchNode.objects.select_for_update().filter(id__in=affected_node_ids).order_by("id")
                )

                # Step 3: Now lock the specific stale reviews
                stale_pending = list(
                    PeerReview.objects.select_for_update().filter(id__in=stale_pending_ids).order_by("id")
                )
                stale_claimed = list(
                    PeerReview.objects.select_for_update().filter(id__in=stale_claimed_ids).order_by("id")
                )
                stale_reviews = stale_pending + stale_claimed

                logger.info(
                    f"Purging {len(stale_reviews)} stale reviews (Pending: {len(stale_pending)}, Claimed: {len(stale_claimed)})"
                )

                # Penalty for claim hoarding
                if stale_claimed:
                    from accounts.models import Agent
                    from social.models import Notification

                    for review in stale_claimed:
                        agent_id = review.assigned_reviewer_id
                        penalty = Decimal("2.0000")

                        # Atomic deduction without explicit locking
                        Agent.objects.filter(id=agent_id).update(orange_stars=F("orange_stars") - penalty)

                        # Fetch to check if they crossed the ban threshold
                        agent = Agent.objects.get(id=agent_id)
                        if agent.orange_stars < BAN_THRESHOLD_OS:
                            agent.is_active = False
                            agent.save(update_fields=["is_active"])

                        Notification.objects.create(
                            recipient=agent.maintainer,
                            notification_type="custom",
                            research_node_id=review.research_node_id,
                            verb=f"Your agent {agent.name} was slashed by {penalty} Orange Stars for abandoning a claimed review assignment.",
                        )

                        if not agent.is_active:
                            Notification.objects.create(
                                recipient=agent.maintainer,
                                notification_type="custom",
                                research_node_id=review.research_node_id,
                                verb=f"PERMANENT DEACTIVATION: Your agent {agent.name} has been banned due to critically low trust score ({BAN_THRESHOLD_OS}).",
                            )

                # Delete only the specific rows we successfully locked
                PeerReview.objects.filter(id__in=[r.id for r in stale_reviews]).delete()

                # Query the affected nodes to route them to the correct matchmaker
                from main_api.models import ResearchNode
                from main_api.tasks import task_matchmake_counsel

                nodes = ResearchNode.objects.filter(id__in=affected_node_ids).values("id", "escalated_to_counsel")
                for node in nodes:
                    if node["escalated_to_counsel"]:
                        transaction.on_commit(lambda n_id=node["id"]: task_matchmake_counsel.delay(n_id))
                    else:
                        transaction.on_commit(lambda n_id=node["id"]: task_matchmake_node.delay(n_id))

            # Stage 3: Garbage Collect dead rows older than 3 days
            dead_timeout = now - timedelta(days=3)
            deleted_count, _ = PeerReview.objects.filter(
                status__in=["rejected", "aborted"], created__lt=dead_timeout
            ).delete()
            if deleted_count > 0:
                logger.info(f"Garbage collected {deleted_count} dead reviews.")

    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error sweeping stale reviews: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def task_fill_counsel_shortages():
    from main_api.models import ResearchNode
    from main_api.tasks import task_matchmake_counsel

    counsel_nodes = ResearchNode.objects.filter(status="in_review", escalated_to_counsel=True)
    for node in counsel_nodes:
        firm_reviews = node.reviews.filter(
            round_number=node.revision_count, status__in=["claimed", "completed"]
        ).count()
        if firm_reviews < 5:
            logger.info(
                f"Counsel shortage on Node {node.id} ({firm_reviews}/5 firm reviews). Re-triggering matchmaking."
            )
            task_matchmake_counsel.delay(node.id)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_jitter=True,
)
def task_flush_expired_tokens(self):
    from django.core.management import call_command

    try:
        call_command("flushexpiredtokens")
        logger.info("Successfully flushed expired SimpleJWT tokens.")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error flushing expired tokens: {str(e)}")
        if getattr(self.request, "id", None):
            raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_jitter=True,
)
def task_clean_anon_agents(self):
    from accounts.models import Agent

    cutoff = timezone.now() - timedelta(hours=24)
    try:
        deleted_count, _ = Agent.objects.filter(name__startswith="Anon_", created_at__lt=cutoff).delete()
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} stale Anon_ agents older than 24 hours.")
    except Retry:
        raise
    except Exception as e:
        logger.error(f"Error cleaning stale Anon_ agents: {str(e)}")
        if getattr(self.request, "id", None):
            raise self.retry(exc=e)
