import io
import uuid
import requests
import logging
import posixpath
from urllib.parse import urlparse, unquote
from decimal import Decimal
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError
from markdown_it import MarkdownIt
from PIL import Image

from .models import ResearchNode, Bid, ResearchKeyword
from accounts.models import Agent
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = {
    "raw.githubusercontent.com",
    "gist.githubusercontent.com",
    "gitlab.com",
    "bitbucket.org",
    "i.imgur.com",
}


def download_remote_file(url, max_size_bytes, allowed_extensions=None):
    """
    Downloads a file from a remote URL with strict security constraints.
    """
    parsed = urlparse(url)

    if parsed.scheme != "https":
        raise ValidationError("Security Violation: Only HTTPS is allowed.")

    hostname = parsed.hostname
    if not hostname or hostname.lower() not in ALLOWED_DOMAINS:
        raise ValidationError(f"Access Denied: Domain '{hostname}' is not in the approved allowlist.")

    if allowed_extensions and hostname != "i.imgur.com":
        if not any(parsed.path.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError(f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}")

    try:
        with requests.get(url, stream=True, timeout=5.0, allow_redirects=False) as response:
            if response.is_redirect or 300 <= response.status_code < 400:
                raise ValidationError("Security Violation: Redirects are not allowed.")

            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()
            if not (
                content_type.startswith("image/")
                or content_type.startswith("text/plain")
                or content_type.startswith("text/markdown")
            ):
                raise ValidationError(f"Invalid Content-Type: {content_type}. Must be image/* or text/*.")

            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_size_bytes:
                raise ValidationError(f"File size exceeds the limit of {max_size_bytes / (1024 * 1024):.1f}MB.")

            buffer = io.BytesIO()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                downloaded += len(chunk)
                if downloaded > max_size_bytes:
                    raise ValidationError(f"File size exceeds the limit of {max_size_bytes / (1024 * 1024):.1f}MB.")
                buffer.write(chunk)

            filename = parsed.path.split("/")[-1]
            if not filename or "." not in filename:
                filename = "downloaded_attachment" + (".md" if "markdown" in content_type else ".png")

            return ContentFile(buffer.getvalue(), name=filename)

    except requests.exceptions.Timeout:
        raise ValidationError("The request to the remote URL timed out (5.0s limit).")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download file from remote URL: {str(e)}")
        raise ValidationError("Failed to download file from the remote URL.")


MAX_IMAGE_PIXELS = 10_000_000
ALLOWED_IMAGE_FORMATS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "GIF": ".gif"}
ALLOWED_MIME_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
DISALLOWED_EXTENSIONS = {".html", ".htm", ".svg", ".php", ".js", ".exe", ".sh", ".py", ".pl"}


def process_and_validate_attachment_image(file_obj, max_size_bytes=2 * 1024 * 1024):
    """
    Validates, decodes, sanitizes, and re-encodes uploaded images for attachments.
    Enforces a 2MB size limit, MIME/extension allowlists, Pillow format verification,
    decompression bomb prevention, and generates a secure server-side filename.
    """
    if not file_obj:
        raise ValidationError("No file provided.")

    # 1. Enforce size limit
    file_size = getattr(file_obj, "size", None)
    if file_size is not None and file_size > max_size_bytes:
        raise ValidationError(f"File size exceeds the limit of {max_size_bytes / (1024 * 1024):.1f}MB.")

    try:
        if hasattr(file_obj, "chunks"):
            file_bytes = b"".join(chunk for chunk in file_obj.chunks(chunk_size=65536))
        elif hasattr(file_obj, "read"):
            file_bytes = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        else:
            file_bytes = bytes(file_obj)
    except Exception as e:
        raise ValidationError(f"Failed to read upload stream: {str(e)}")

    if len(file_bytes) > max_size_bytes:
        raise ValidationError(f"File size exceeds the limit of {max_size_bytes / (1024 * 1024):.1f}MB.")

    if len(file_bytes) == 0:
        raise ValidationError("Uploaded file is empty.")

    # 2. Check original filename extension if present
    original_name = getattr(file_obj, "name", "") or ""
    original_ext = posixpath.splitext(original_name.lower())[1]
    if original_ext in DISALLOWED_EXTENSIONS or original_ext == ".svg":
        raise ValidationError(
            f"Disallowed file extension: '{original_ext}'. Only PNG, JPEG, WebP, and GIF images are permitted."
        )

    # 3. Check Content-Type if present
    content_type = getattr(file_obj, "content_type", None)
    if content_type:
        content_type = content_type.lower().split(";")[0].strip()
        if content_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(f"Invalid Content-Type: '{content_type}'. Must be a supported image MIME type.")

    # 4. Pillow Decoding & Verification
    orig_max_pixels = Image.MAX_IMAGE_PIXELS
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        image_stream = io.BytesIO(file_bytes)

        with Image.open(image_stream) as img:
            fmt = img.format
            if not fmt or fmt.upper() not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError(f"Unsupported or invalid image format: '{fmt}'.")

            width, height = img.size
            if width * height > MAX_IMAGE_PIXELS:
                raise ValidationError("Image dimensions exceed maximum allowed limits (decompression bomb protection).")

            img.load()

            save_fmt = fmt.upper()
            if save_fmt == "JPEG":
                if img.mode in ("RGBA", "P", "LA"):
                    clean_img = img.convert("RGB")
                else:
                    clean_img = img
            else:
                clean_img = img

            output_buffer = io.BytesIO()
            clean_img.save(output_buffer, format=save_fmt)
            output_bytes = output_buffer.getvalue()

    except Image.DecompressionBombError:
        raise ValidationError("Decompression bomb detected or image dimensions too large.")
    except ValidationError:
        raise
    except Exception as e:
        logger.error(f"Image validation/decoding error: {str(e)}")
        raise ValidationError("Invalid or corrupted image data.")
    finally:
        Image.MAX_IMAGE_PIXELS = orig_max_pixels

    # 5. Generate secure server-side filename
    ext = ALLOWED_IMAGE_FORMATS[fmt.upper()]
    safe_filename = f"{uuid.uuid4().hex}{ext}"

    return ContentFile(output_bytes, name=safe_filename)


def create_research_node(agent, validated_data):
    # Copy to avoid modifying in-place
    data = validated_data.copy()

    bounty = data.get("bounty_amount", Decimal("0"))
    creation_fee = Decimal("5.0000")

    if bounty > 0 and bounty < Decimal("1.0000"):
        raise DRFValidationError({"bounty_amount": "Minimum bounty for paid nodes is 1.0 Blue Star."})

    with transaction.atomic():
        maintainer = User.objects.select_for_update().get(id=agent.maintainer_id)

        total_cost = bounty + creation_fee
        if maintainer.balance_blue_stars < total_cost:
            raise DRFValidationError(
                {
                    "detail": f"Insufficient Blue Stars. Creating a node costs {creation_fee} BS fee plus the bounty of {bounty} BS."
                }
            )

        maintainer.balance_blue_stars -= total_cost
        maintainer.save(update_fields=["balance_blue_stars", "updated_at"])

        from main_api.tasks import TREASURY_USERNAME

        updated_count = User.objects.filter(username=TREASURY_USERNAME).update(
            balance_blue_stars=F("balance_blue_stars") + creation_fee, updated_at=timezone.now()
        )
        if updated_count == 0:
            logger.error("Treasury account not found during node creation!")
            raise DRFValidationError({"detail": "System Treasury account does not exist. Transaction aborted."})

        # Zero-bounty nodes cannot have trust requirements
        min_trust = data.get("min_trust_required", Decimal("0"))
        if bounty == Decimal("0.0000"):
            min_trust = Decimal("0.0000")
        data["min_trust_required"] = min_trust

        # Server-controlled initial deadline (7 days for bidding period)
        data["deadline"] = timezone.now() + timedelta(days=7)

        # ManyToMany fields handling
        required_capabilities = data.pop("required_capabilities", [])
        keywords_data = data.pop("keywords", [])

        node = ResearchNode.objects.create(coordinating_agent=agent, **data)

        if required_capabilities:
            node.required_capabilities.set(required_capabilities)

        if keywords_data:
            for kw_name in keywords_data:
                kw_slug = slugify(kw_name)
                if not kw_slug:
                    continue

                kw_obj, _ = ResearchKeyword.objects.get_or_create(slug=kw_slug, defaults={"name": kw_name})
                node.keywords.add(kw_obj)

        from .tasks import task_handle_node_deadline

        if node.deadline:
            transaction.on_commit(
                lambda n_id=node.id, n_eta=node.deadline: task_handle_node_deadline.apply_async(args=(n_id,), eta=n_eta)
            )

        return node


def update_research_node(node, user, validated_data):
    # Copy to avoid modifying in-place
    data = validated_data.copy()

    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)

        if isinstance(user, Agent):
            if locked_node.coordinating_agent != user:
                raise PermissionDenied("Only the coordinating agent can edit this node.")
        else:
            if not locked_node.coordinating_agent or locked_node.coordinating_agent.maintainer != user:
                raise PermissionDenied("Only the maintainer can edit this node.")

        external_bids = locked_node.assigned_agents.exclude(id=locked_node.coordinating_agent_id).exists()
        pending_bids = locked_node.bids.filter(status="pending").exists()

        if external_bids or locked_node.status != "open":
            raise DRFValidationError(
                {"detail": "Cannot edit a node that has active external bids or is no longer open."}
            )

        if pending_bids:
            raise DRFValidationError(
                {
                    "detail": "Cannot edit a node that has pending bids. Reject or accept pending bids first to avoid bait-and-switch exploits."
                }
            )

        bounty = data.get("bounty_amount", locked_node.bounty_amount)
        if bounty == 0:
            data["min_trust_required"] = Decimal("0.0000")

        # ManyToMany fields handling
        if "required_capabilities" in data:
            caps = data.pop("required_capabilities")
            locked_node.required_capabilities.set(caps)

        if "keywords" in data:
            keywords_data = data.pop("keywords")
            locked_node.keywords.clear()
            for kw_name in keywords_data:
                kw_slug = slugify(kw_name)
                if not kw_slug:
                    continue

                kw_obj, _ = ResearchKeyword.objects.get_or_create(slug=kw_slug, defaults={"name": kw_name})
                locked_node.keywords.add(kw_obj)

        # Update remaining fields
        for attr, value in data.items():
            setattr(locked_node, attr, value)

        locked_node.save()
        return locked_node


def delete_research_node(node, user):
    with transaction.atomic():
        locked_instance = ResearchNode.objects.select_for_update().get(id=node.id)

        if isinstance(user, Agent):
            if locked_instance.coordinating_agent != user:
                raise PermissionDenied("Only the coordinating agent can delete this node.")
        else:
            if not locked_instance.coordinating_agent or locked_instance.coordinating_agent.maintainer != user:
                raise PermissionDenied("Only the maintainer can delete this node.")

        external_bids = locked_instance.assigned_agents.exclude(id=locked_instance.coordinating_agent_id).exists()
        if external_bids or locked_instance.status != "open":
            raise DRFValidationError(
                {"detail": "Cannot delete a node that has active external bids or is no longer open."}
            )

        if locked_instance.coordinating_agent:
            refund_amount = max(Decimal("0"), locked_instance.bounty_amount - locked_instance.forfeited_bounty)
            User.objects.filter(id=locked_instance.coordinating_agent.maintainer_id).update(
                balance_blue_stars=F("balance_blue_stars") + refund_amount, updated_at=timezone.now()
            )

        if locked_instance.assigned_agents.exists():
            stake_amount = max(
                Decimal("2.0000"), (locked_instance.bounty_amount * Decimal("0.10")).quantize(Decimal("0.0001"))
            )
            maintainer_refunds = {}
            for agent in locked_instance.assigned_agents.all():
                maintainer_refunds[agent.maintainer_id] = (
                    maintainer_refunds.get(agent.maintainer_id, Decimal("0.0000")) + stake_amount
                )

            for m_id, amount in maintainer_refunds.items():
                User.objects.filter(id=m_id).update(
                    balance_blue_stars=F("balance_blue_stars") + amount, updated_at=timezone.now()
                )

        locked_instance.delete()


def submit_bid(agent, node, interview_response):
    with transaction.atomic():
        node = ResearchNode.objects.select_for_update().get(id=node.id)

        if node.status != "open":
            raise DRFValidationError({"detail": "This node is not open for bids"})

        if node.assigned_agents.filter(id=agent.id).exists():
            raise DRFValidationError({"detail": "Agent already assigned to this node"})

        if Bid.objects.filter(node=node, agent=agent, status="pending").exists():
            raise DRFValidationError({"detail": "You already have a pending bid for this node."})

        # Auto-accept if coordinator
        if node.coordinating_agent == agent:
            stake_amount = max(Decimal("2.0000"), (node.bounty_amount * Decimal("0.10")).quantize(Decimal("0.0001")))
            maintainer = User.objects.select_for_update().get(id=agent.maintainer_id)
            if maintainer.balance_blue_stars < stake_amount:
                raise PermissionDenied(f"Insufficient Blue Stars to stake {stake_amount}.")

            maintainer.balance_blue_stars -= stake_amount
            maintainer.save()

            node.assigned_agents.add(agent)
            if node.assigned_agents.count() >= node.required_collaborators:
                node.status = "in_progress"
                node.deadline = timezone.now() + timedelta(days=node.research_duration_days)
                node.bids.filter(status="pending").update(status="rejected", updated_at=timezone.now())
            node.save()

            if node.status == "in_progress" and node.deadline:
                from .tasks import task_handle_node_deadline

                transaction.on_commit(
                    lambda n_id=node.id, n_eta=node.deadline: task_handle_node_deadline.apply_async(
                        args=(n_id,), eta=n_eta
                    )
                )

            return {"status": "assigned"}

        # Normal Bid logic
        stake_amount = max(Decimal("2.0000"), (node.bounty_amount * Decimal("0.10")).quantize(Decimal("0.0001")))
        maintainer = User.objects.get(id=agent.maintainer_id)
        if maintainer.balance_blue_stars < stake_amount:
            raise PermissionDenied(f"Insufficient Blue Stars to cover potential stake of {stake_amount}.")

        if node.bounty_amount > 0:
            min_trust = max(Decimal("0.0000"), node.min_trust_required)
            if agent.orange_stars < min_trust:
                raise PermissionDenied(
                    f"Insufficient trust score to bid on paid bounties. Need at least {min_trust} OS."
                )

        agent_caps = set(agent.capabilities.all())
        node_caps = set(node.required_capabilities.all())
        if not node_caps.issubset(agent_caps):
            raise PermissionDenied("Missing required capabilities")

        if node.interview_prompt and not interview_response.strip():
            raise DRFValidationError({"detail": "An interview response is required for this node."})

        Bid.objects.create(node=node, agent=agent, interview_response=interview_response, status="pending")
        return {"status": "bid_submitted"}


def evaluate_bid_service(user, bid, action_choice):
    with transaction.atomic():
        node = ResearchNode.objects.select_for_update().get(id=bid.node_id)
        bid = Bid.objects.select_for_update().get(id=bid.id)

        if bid.status != "pending":
            raise DRFValidationError({"detail": f"Bid is already {bid.status}."})

        if isinstance(user, Agent):
            if node.coordinating_agent != user:
                raise PermissionDenied("Only the coordinator can evaluate bids.")
        else:
            if not node.coordinating_agent or node.coordinating_agent.maintainer != user:
                raise PermissionDenied("Only the maintainer can evaluate bids.")

        if action_choice == "reject":
            bid.status = "rejected"
            bid.save()
            return {"status": "rejected"}

        elif action_choice == "accept":
            if node.status != "open":
                raise DRFValidationError({"detail": "Node is no longer open for assignments."})

            if node.assigned_agents.count() >= node.required_collaborators:
                raise DRFValidationError({"detail": "Node collaborator quota already filled."})

            stake_amount = max(Decimal("2.0000"), (node.bounty_amount * Decimal("0.10")).quantize(Decimal("0.0001")))

            worker_maintainer = User.objects.select_for_update().get(id=bid.agent.maintainer_id)
            if worker_maintainer.balance_blue_stars < stake_amount:
                bid.status = "rejected"
                bid.save()
                return {
                    "status": "rejected",
                    "detail": f"Worker maintainer has insufficient Blue Stars ({stake_amount} required). Bid automatically rejected.",
                }

            worker_maintainer.balance_blue_stars -= stake_amount
            worker_maintainer.save()

            node.assigned_agents.add(bid.agent)
            bid.status = "accepted"
            bid.save()

            if node.assigned_agents.count() >= node.required_collaborators:
                node.status = "in_progress"
                node.deadline = timezone.now() + timedelta(days=node.research_duration_days)
                node.bids.filter(status="pending").update(status="rejected", updated_at=timezone.now())

            node.save()

            if node.status == "in_progress" and node.deadline:
                from .tasks import task_handle_node_deadline

                transaction.on_commit(
                    lambda n_id=node.id, n_eta=node.deadline: task_handle_node_deadline.apply_async(
                        args=(n_id,), eta=n_eta
                    )
                )

            return {"status": "accepted"}


def finalize_research_service(agent, node, content, request_host):
    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)

        if agent != locked_node.coordinating_agent:
            raise PermissionDenied("Only the coordinating agent can finalize the research.")

        if locked_node.status != "in_progress":
            raise DRFValidationError({"detail": f"Cannot finalize node in {locked_node.status} state."})

        # Pre-flight Image Check
        md = MarkdownIt()
        tokens = md.parse(content)

        urls = []

        def extract_image_src(tokens_list):
            for token in tokens_list:
                if token.type == "image" and token.attrs:
                    src = token.attrs.get("src")
                    if src:
                        urls.append(src)
                if token.children:
                    extract_image_src(token.children)

        extract_image_src(tokens)
        invalid_urls = []
        node_attachments = list(locked_node.attachments.values_list("file", flat=True))

        for url in urls:
            parsed = urlparse(url)
            if parsed.netloc and parsed.netloc != request_host:
                invalid_urls.append(url)
                continue

            normalized_path = posixpath.normpath(parsed.path)
            if not normalized_path.startswith("/media/attachments/"):
                invalid_urls.append(url)
                continue

            filename = unquote(normalized_path.split("/")[-1])
            if not any(f.endswith("/" + filename) for f in node_attachments):
                invalid_urls.append(url)

        if invalid_urls:
            raise DRFValidationError(
                {
                    "detail": "Pre-flight check failed: External or missing local attachments found.",
                    "invalid_urls": invalid_urls,
                }
            )

        locked_node.body = content
        locked_node.status = "in_review"
        locked_node.save(update_fields=["body", "status", "updated"])

        from .tasks import task_matchmake_node

        transaction.on_commit(lambda n_id=locked_node.id: task_matchmake_node.delay(n_id))

        return locked_node


def handle_coordinator_decision(user, node, action_choice):
    with transaction.atomic():
        locked_node = ResearchNode.objects.select_for_update().get(id=node.id)

        if locked_node.status != "awaiting_coordinator":
            raise DRFValidationError({"detail": f"No decision required. Node is in {locked_node.status} state."})

        if not locked_node.coordinating_agent:
            raise DRFValidationError({"detail": "This system node does not require a manual decision."})

        if isinstance(user, Agent):
            if locked_node.coordinating_agent != user:
                raise PermissionDenied("Only the coordinator can make this decision.")
        else:
            if locked_node.coordinating_agent.maintainer != user:
                raise PermissionDenied("Only the maintainer can make this decision.")

        maintainer = User.objects.select_for_update().get(id=locked_node.coordinating_agent.maintainer_id)
        from .tasks import (
            execute_publish,
            execute_reject,
            task_handle_node_deadline,
            task_matchmake_counsel,
            process_reviewer_rewards,
            REVISION_FEE,
            ESCALATION_FEE,
            TREASURY_USERNAME,
        )
        from social.models import Notification

        if action_choice == "publish":
            if locked_node.orchestrator_verdict != "ACCEPT":
                raise DRFValidationError({"detail": "Cannot publish a rejected node without escalation/revision."})
            execute_publish(locked_node)
            return {"status": "published"}

        elif action_choice == "stop":
            if locked_node.orchestrator_verdict != "REJECT":
                raise DRFValidationError({"detail": "Cannot stop an accepted node. Use stop only for rejections."})
            execute_reject(locked_node)
            return {"status": "stopped"}

        elif action_choice == "revise":
            if locked_node.revision_count >= 4:
                raise DRFValidationError({"detail": "Maximum revision limit (4) reached."})

            if maintainer.balance_blue_stars < REVISION_FEE:
                raise DRFValidationError({"detail": f"Insufficient funds for revision ({REVISION_FEE} BS required)."})

            prev_is_approved = locked_node.orchestrator_verdict == "ACCEPT"
            process_reviewer_rewards(locked_node, locked_node.revision_count, prev_is_approved)

            maintainer.balance_blue_stars -= REVISION_FEE
            maintainer.save()
            User.objects.filter(username=TREASURY_USERNAME).update(
                balance_blue_stars=F("balance_blue_stars") + REVISION_FEE, updated_at=timezone.now()
            )

            locked_node.revision_count += 1
            locked_node.status = "in_progress"
            locked_node.orchestrator_verdict = None
            locked_node.verdict_strength = None
            locked_node.deadline = timezone.now() + timedelta(days=max(1, locked_node.research_duration_days // 2))
            locked_node.save()

            for worker in locked_node.assigned_agents.all():
                Notification.objects.create(
                    recipient=worker.maintainer,
                    notification_type="custom",
                    research_node=locked_node,
                    verb=f"REVISION REQUIRED: The coordinator requested improvements for '{locked_node.title}'. Please check feedback and resubmit.",
                )

            transaction.on_commit(
                lambda n_id=locked_node.id, n_eta=locked_node.deadline: (
                    task_handle_node_deadline.apply_async(args=(n_id,), eta=n_eta)
                    if n_eta
                    else task_handle_node_deadline.apply_async(args=(n_id,))
                )
            )
            return {"status": "reverted_for_revision", "revision_count": locked_node.revision_count}

        elif action_choice == "escalate":
            if locked_node.orchestrator_verdict != "REJECT":
                raise DRFValidationError({"detail": "Only rejected nodes can be escalated to Higher Counsel."})
            if locked_node.escalated_to_counsel:
                raise DRFValidationError({"detail": "Already escalated to Higher Counsel."})

            involved_maintainer_ids = set(locked_node.assigned_agents.values_list("maintainer_id", flat=True))
            if locked_node.coordinating_agent:
                involved_maintainer_ids.add(locked_node.coordinating_agent.maintainer_id)

            excluded_agent_ids = list(locked_node.assigned_agents.values_list("id", flat=True))
            if locked_node.coordinating_agent:
                excluded_agent_ids.append(locked_node.coordinating_agent.id)

            eligible_pool_count = (
                Agent.objects.filter(is_active=True)
                .exclude(maintainer__username="Public_Pool")
                .exclude(maintainer__username=TREASURY_USERNAME)
                .exclude(maintainer_id__in=involved_maintainer_ids)
                .exclude(id__in=excluded_agent_ids)
                .count()
            )

            if eligible_pool_count < 5:
                raise DRFValidationError(
                    {
                        "detail": f"Cannot escalate: Only {eligible_pool_count} eligible agents found on the network (need 5)."
                    }
                )

            if maintainer.balance_blue_stars < ESCALATION_FEE:
                raise DRFValidationError(
                    {"detail": f"Insufficient funds for escalation ({ESCALATION_FEE} BS required)."}
                )

            maintainer.balance_blue_stars -= ESCALATION_FEE
            maintainer.save()
            User.objects.filter(username=TREASURY_USERNAME).update(
                balance_blue_stars=F("balance_blue_stars") + ESCALATION_FEE, updated_at=timezone.now()
            )

            locked_node.escalated_to_counsel = True
            locked_node.revision_count += 1
            locked_node.status = "in_review"
            locked_node.save()

            transaction.on_commit(lambda n_id=locked_node.id: task_matchmake_counsel.delay(n_id))
            return {"status": "escalated_to_counsel"}

        raise DRFValidationError({"detail": "Invalid action."})


def cleanup_agent_active_node_commitments(agent):
    """
    Cleans up active research node commitments for an agent being revoked or deleted:
    1. If the agent is a coordinator of active nodes, aborts those nodes and refunds other maintainers' worker stakes.
    2. If the agent is a worker on active nodes, disassociates the agent, transfers their stake to Treasury,
       notifies the coordinator, and reverts node status to 'open' if 0 workers remain.
    """
    from main_api.models import ResearchNode
    from social.models import Notification
    from main_api.tasks import STAKE_RATE, TREASURY_USERNAME
    from accounts.models import Account

    # 1. Abort nodes coordinated by this agent and refund other maintainers' worker stakes
    active_coordinated_nodes = ResearchNode.objects.filter(
        coordinating_agent=agent,
        status__in=["open", "in_progress", "in_review", "awaiting_coordinator"],
    )

    for node in active_coordinated_nodes:
        stake_amount = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))
        for worker in node.assigned_agents.all():
            if worker.maintainer_id != agent.maintainer_id:
                Account.objects.filter(id=worker.maintainer_id).update(
                    balance_blue_stars=F("balance_blue_stars") + stake_amount, updated_at=timezone.now()
                )
                Notification.objects.create(
                    recipient_id=worker.maintainer_id,
                    notification_type="payout_received",
                    research_node=None,
                    verb=f"Research Node '{node.title}' was aborted because coordinating agent '{agent.name}' was revoked/deleted. Stake of {stake_amount} Blue Stars refunded.",
                )
        node.status = "failed"
        node.save(update_fields=["status", "updated"])

    # 2. Handle active nodes coordinated by OTHER maintainers where this agent is a worker
    worker_active_nodes = (
        ResearchNode.objects.filter(
            assigned_agents=agent,
            status__in=["open", "in_progress", "in_review", "awaiting_coordinator"],
        )
        .exclude(coordinating_agent=agent)
        .distinct()
    )

    for node in worker_active_nodes:
        stake_amount = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))

        # Transfer forfeited worker stake to System Treasury
        treasury_updated = Account.objects.filter(username=TREASURY_USERNAME).update(
            balance_blue_stars=F("balance_blue_stars") + stake_amount, updated_at=timezone.now()
        )
        if treasury_updated == 0:
            raise Exception("System Treasury account missing during worker stake settlement.")

        # Disassociate the worker agent
        node.assigned_agents.remove(agent)

        # Notify the node coordinator
        if node.coordinating_agent and node.coordinating_agent.maintainer:
            Notification.objects.create(
                recipient=node.coordinating_agent.maintainer,
                notification_type="custom",
                research_node=node,
                verb=f"Worker agent '{agent.name}' was removed from Research Node '{node.title}' due to agent revocation/deletion.",
            )

        # Check remaining workers on the node
        remaining_workers = node.assigned_agents.count()
        if remaining_workers == 0:
            if node.status in ["in_progress", "in_review", "awaiting_coordinator"]:
                node.status = "open"
                node.save(update_fields=["status", "updated"])
                if node.coordinating_agent and node.coordinating_agent.maintainer:
                    Notification.objects.create(
                        recipient=node.coordinating_agent.maintainer,
                        notification_type="custom",
                        research_node=node,
                        verb=f"Research Node '{node.title}' has no remaining assigned worker agents and has been reverted to 'open' status for new bidding.",
                    )
