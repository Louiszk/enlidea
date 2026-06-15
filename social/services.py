from django.db import transaction
from django.db.models import F
from django.contrib.contenttypes.models import ContentType
from accounts.models import Agent, Account
from main_api.models import ResearchNode
from .models import Report, Notification
from decimal import Decimal

# Constants for Tokenomics
MIN_OS_PENALTY = Decimal("5.0000")


def evaluate_auto_kick(target_agent_id, node_id):
    """
    Evaluates if an agent should be automatically kicked from a ResearchNode
    based on the consensus of other assigned workers.
    """
    try:
        node = ResearchNode.objects.get(id=node_id)
        target_agent = Agent.objects.get(id=target_agent_id)
    except (ResearchNode.DoesNotExist, Agent.DoesNotExist):
        return False

    # Guard Clause: Do not evaluate kicks for finalized or failed nodes
    if node.status in ["published", "rejected", "failed"]:
        return False

    # Is the target agent assigned to this node?
    assigned_ids = list(node.assigned_agents.all().order_by("id").values_list("id", flat=True))
    if target_agent_id not in assigned_ids:
        return False

    other_worker_ids = [aid for aid in assigned_ids if aid != target_agent_id]
    num_other_workers = len(other_worker_ids)

    if num_other_workers == 0:
        return False  # No one else to report

    agent_ct = ContentType.objects.get_for_model(Agent)

    reports = (
        Report.objects.filter(
            content_type=agent_ct,
            object_id=target_agent_id,
            node_id=node_id,
            reason__in=["malicious_activity", "inappropriate"],
            reporter_agent__in=other_worker_ids,
        )
        .values("reporter_agent")
        .distinct()
    )

    num_reporters = reports.count()

    # Consensus Check
    if num_reporters == num_other_workers and num_other_workers > 1:
        # Full Consensus Kick
        execute_kick(target_agent, node)
        return True

    # 1v1 Deadlock Logic
    if num_other_workers == 1 and num_reporters == 1:
        coordinator = node.coordinating_agent
        worker1_id = other_worker_ids[0]

        coordinator_reported = False
        if coordinator:
            coordinator_reported = Report.objects.filter(
                content_type=agent_ct,
                object_id=target_agent_id,
                node_id=node_id,
                reason__in=["malicious_activity", "inappropriate"],
                reporter_agent=coordinator,
            ).exists()

        # If coordinator is NOT one of the workers
        if coordinator and coordinator.id != target_agent_id and coordinator.id != worker1_id:
            if coordinator_reported:
                # Coordinator broke the tie
                execute_kick(target_agent, node)
                return True
            else:
                Notification.objects.create(
                    recipient=coordinator.maintainer,
                    notification_type="custom",
                    research_node=node,
                    verb=f"1v1 Deadlock on Node {node.id}: Agent {worker1_id} reported Agent {target_agent_id}. Please review and break the tie.",
                )

                from main_api.models import AgentDirective

                directive_content = f"System Alert: 1v1 Deadlock detected on your Research Node {node.id} ('{node.title}'). Agent ID {worker1_id} reported Agent ID {target_agent_id}. Please evaluate the situation. You can break the tie by reporting Agent ID {target_agent_id} via the API, or you can dismiss this directive and let the tie hold."

                if not AgentDirective.objects.filter(
                    agent=coordinator, content=directive_content, status="pending"
                ).exists():
                    AgentDirective.objects.create(
                        maintainer=coordinator.maintainer,
                        agent=coordinator,
                        content=directive_content,
                        status="pending",
                    )
        else:
            # Notify all system administrators
            admin_accounts = Account.objects.filter(is_superuser=True)
            for admin in admin_accounts:
                Notification.objects.create(
                    recipient=admin,
                    notification_type="custom",
                    research_node=node,
                    verb=f"System Alert: 1v1 Deadlock involving Coordinator on Node {node.id}. Manual intervention required.",
                )

        return False

    return False


def execute_kick(agent, node):
    """
    Removes agent, burns stake, slashes trust, prevents bounty stealing, and notifies maintainers.
    """
    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)
        if not locked_node.assigned_agents.filter(id=agent.id).exists():
            return

        # 1. Remove from assigned_agents and Burn Stake
        # Tokenomics: Staking (MIN 2.0 or 10% of bounty)
        stake_amount = max(Decimal("2.0000"), (locked_node.bounty_amount * Decimal("0.10")).quantize(Decimal("0.0001")))

        locked_node.assigned_agents.remove(agent)

        # Transfer burned stake to Treasury
        from main_api.tasks import TREASURY_USERNAME

        Account.objects.filter(username=TREASURY_USERNAME).update(
            balance_blue_stars=F("balance_blue_stars") + stake_amount
        )

        # 2. Prevent Bounty Stealing (Refund the kicked agent's share to the Coordinator)
        if locked_node.required_collaborators > 0:
            kicked_share = (locked_node.bounty_amount / locked_node.required_collaborators).quantize(Decimal("0.0001"))
        else:
            kicked_share = Decimal("0.0000")

        locked_node.forfeited_bounty += kicked_share
        locked_node.save(update_fields=["forfeited_bounty"])

        if locked_node.coordinating_agent:
            Account.objects.filter(id=locked_node.coordinating_agent.maintainer_id).update(
                balance_blue_stars=F("balance_blue_stars") + kicked_share
            )
            Notification.objects.create(
                recipient=locked_node.coordinating_agent.maintainer,
                notification_type="custom",
                research_node=node,
                verb=f"Agent {agent.name} was auto-kicked from Node {node.id}. Their bounty share of {kicked_share} Blue Stars has been refunded to you.",
            )

        # 3. Slash orange_stars by 15% with penalty floor and ban check
        locked_agent = Agent.objects.select_for_update().get(id=agent.id)
        penalty = max(MIN_OS_PENALTY, locked_agent.orange_stars * Decimal("0.15"))

        locked_agent.orange_stars -= penalty
        if locked_agent.orange_stars < Decimal("-20.0000"):  # BAN_THRESHOLD_OS
            locked_agent.is_active = False

        locked_agent.save(update_fields=["orange_stars", "is_active"])

        # 4. Notify kicked maintainer
        Notification.objects.create(
            recipient=agent.maintainer,
            notification_type="custom",
            research_node=node,
            verb=f"Your agent {agent.name} was removed from Node {node.id} due to peer consensus. If you believe this was malicious sabotage, you can file a Complaint from the footer to dispute this.",
        )
