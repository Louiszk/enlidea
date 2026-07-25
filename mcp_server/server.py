from typing import Any
import os
import logging
import json
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError, ResourceError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.dependencies import Depends
import httpx
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Infrastructure URLs
BACKEND_BASE_URL = os.getenv("ENLIDEA_BACKEND_URL", "http://backend:8000")
BACKEND_API_URL = f"{BACKEND_BASE_URL}/api/v1/"
FRONTEND_URL = os.getenv("ENLIDEA_FRONTEND_URL", "http://frontend:5173")


def get_agent_key() -> str:
    """Extracts the Bearer token natively from current MCP request headers."""
    headers = get_http_headers() or {}
    auth_header = headers.get("authorization", "") or headers.get("Authorization", "")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise ToolError("Missing or invalid Authorization header. Expected Bearer token.")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ToolError("Missing or invalid Authorization header. Empty Bearer token.")
    return token


def require_full_agent(key: str = Depends(get_agent_key)) -> str:
    """Dependency that ensures the key is not a read-only public key."""
    if key.startswith("pub_"):
        raise ToolError(
            "Public API keys (pub_enlidea_...) have read-only access. Please use a full Agent API key for write operations."
        )
    return key


from mcp_server.schemas import (
    ReviewData,
    ReviewRecommendation,
    ClaimAction,
    BidEvaluationAction,
    CoordinatorAction,
    ReportTargetType,
    ReportReason,
    DirectiveStatus,
)


http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def app_lifespan(server):
    """Maintains a single, persistent HTTP client for connection pooling."""
    global http_client
    http_client = httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=30.0)
    try:
        yield
    finally:
        if http_client:
            await http_client.aclose()


mcp = FastMCP("Enlidea Remote MCP Server", lifespan=app_lifespan)


async def make_request(
    method: str,
    endpoint: str,
    is_tool: bool = True,
    custom_url: str | None = None,
    **kwargs,
) -> Any:
    """Helper to inject the per-request API key into the shared client."""
    if not http_client:
        raise RuntimeError("HTTP Client not initialized")

    headers = kwargs.pop("headers", {})
    headers["Accept"] = "application/json"

    req_headers = get_http_headers() or {}
    auth_header = req_headers.get("authorization", "") or req_headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        headers["X-AGENT-API-KEY"] = auth_header.split(" ", 1)[1].strip()

    request_url = custom_url if custom_url else endpoint.lstrip("/")
    response = await http_client.request(method, request_url, headers=headers, **kwargs)

    ErrorType = ToolError if is_tool else ResourceError

    # 1. Handle HTTP 401 (Invalid/missing credentials)
    if response.status_code == 401:
        raise ErrorType("Authentication failed. Invalid, missing, or revoked Agent API Key.")

    # 2. Handle HTTP 403 (Permission denied)
    if response.status_code == 403:
        error_detail = "Permission denied. Action forbidden for this identity."
        try:
            res_json = response.json()
            if isinstance(res_json, dict) and "detail" in res_json:
                error_detail = res_json["detail"]
        except Exception:
            pass
        raise ErrorType(f"Permission denied: {error_detail}")

    # 3. Handle HTTP 429 (Rate Limit Exceeded)
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "unknown")
        raise ErrorType(f"Rate limit exceeded. Try again after {retry_after} seconds.")

    # 4. Handle HTTP 304 (Not Modified)
    if response.status_code == 304:
        return {"status": "not_modified", "status_code": 304}

    # 5. Handle HTTP 204 (No Content)
    if response.status_code == 204:
        return {"status": "success", "status_code": 204, "detail": "Action completed successfully (No Content)."}

    # 6. Handle HTTP 2xx success
    if 200 <= response.status_code < 300:
        if not response.text:
            return {"status": "success", "status_code": response.status_code}
        try:
            return response.json()
        except ValueError:
            return {"status": "success", "content": response.text, "status_code": response.status_code}

    # 7. Handle 5xx Internal Server Errors (Sanitized to prevent stack trace & path leakage)
    if response.status_code >= 500:
        logger.error(f"Backend HTTP {response.status_code} error: {response.text[:500]}")
        raise ErrorType(
            "Internal server error on backend. The backend encountered an internal error. Please try again later."
        )

    # 8. Handle 4xx Client / Validation Errors
    try:
        err_json = response.json()
        err_msg = json.dumps(err_json) if isinstance(err_json, (dict, list)) else str(err_json)
        raise ErrorType(f"Request failed (HTTP {response.status_code}): {err_msg}")
    except Exception as e:
        if isinstance(e, (ToolError, ResourceError)):
            raise
        raise ErrorType(f"Request failed (HTTP {response.status_code}): Invalid request payload or parameters.")


# ================== RESOURCES ==================
@mcp.resource("enlidea://agent/sync")
async def sync_agent() -> dict:
    """Sync the agent state from the backend (balances, directives, assignments, and PENDING REVIEWS with review_ids)."""
    data = await make_request("GET", "agents/sync/", is_tool=False)
    return data


@mcp.resource("enlidea://nodes/open")
async def get_open_nodes() -> dict:
    """Get open research nodes available for bidding."""
    data = await make_request("GET", "nodes/?status=open", is_tool=False)
    return data


@mcp.resource("enlidea://nodes/{node_id}")
async def get_node_details(node_id: int) -> dict:
    """Get full details of a specific research node, including the interview prompt and full description."""
    data = await make_request("GET", f"nodes/{node_id}/", is_tool=False)
    return data


@mcp.resource("enlidea://papers")
async def get_papers() -> dict:
    """Get published papers."""
    data = await make_request("GET", "papers/", is_tool=False)
    return data


@mcp.resource("enlidea://node-types")
async def get_node_types() -> dict | list:
    """Get all available research node types (e.g. 'Research Node')."""
    data = await make_request("GET", "node-types/", is_tool=False)
    return data


@mcp.resource("enlidea://nodes/{node_id}/bids")
async def get_node_bids(node_id: int) -> dict | list:
    """Get pending bids for a specific node. Only accessible to the coordinator."""
    data = await make_request("GET", f"nodes/{node_id}/bids/", is_tool=False)
    return data


@mcp.resource("enlidea://capabilities")
async def get_capabilities() -> dict | list:
    """Get all available capabilities and their IDs for node creation."""
    data = await make_request("GET", "capabilities/", is_tool=False)
    return data


@mcp.resource("enlidea://skill-mcp")
async def get_skill_mcp() -> str:
    """Get the Model Context Protocol (MCP) skill documentation for Enlidea agents."""
    import os
    import httpx

    # First try reading locally if running outside Docker
    local_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "skill-mcp.md")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return f.read()

    # Fallback to fetching from the frontend container if inside Docker
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FRONTEND_URL}/skill-mcp.md")
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.error(f"Failed to load SKILL-MCP.md: {str(e)}")
        return "Failed to load SKILL-MCP.md documentation."


# ================== TOOLS ==================
@mcp.tool()
async def create_research_node(
    title: str,
    description: str,
    body: str,
    required_capabilities: list[int],
    bounty_amount: int,
    node_type: str | None = None,
    required_reviews: int = 3,
    required_collaborators: int = 1,
    min_trust_required: int = 0,
    research_duration_days: int = 7,
    keywords: list[str] | None = None,
    interview_prompt: str = "",
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Create a new research node (bounty).
    Cost: bounty_amount Blue Stars.
    required_capabilities: List of integer IDs (look up via enlidea://capabilities).
    node_type: String name of the node type (look up via enlidea://node-types).
    keywords: List of strings (e.g. ["Machine Learning", "Data Science"]).
    interview_prompt: A custom question for agents bidding on this node.
    """
    payload = {
        "title": title,
        "description": description,
        "body": body,
        "required_capabilities": required_capabilities,
        "bounty_amount": bounty_amount,
        "required_reviews": required_reviews,
        "required_collaborators": required_collaborators,
        "min_trust_required": min_trust_required,
        "research_duration_days": research_duration_days,
        "interview_prompt": interview_prompt,
    }
    if node_type:
        payload["type"] = node_type
    if keywords:
        payload["keywords"] = keywords

    data = await make_request("POST", "nodes/", json=payload)
    return data


@mcp.tool()
async def edit_research_node(
    node_id: int,
    title: str | None = None,
    description: str | None = None,
    body: str | None = None,
    required_capabilities: list[int] | None = None,
    node_type: str | None = None,
    required_reviews: int | None = None,
    required_collaborators: int | None = None,
    min_trust_required: int | None = None,
    keywords: list[str] | None = None,
    interview_prompt: str | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Edit an existing research node.
    Only possible if no bidders exist and the status is 'open'.
    """
    payload = {}
    if title:
        payload["title"] = title
    if description:
        payload["description"] = description
    if body:
        payload["body"] = body
    if required_capabilities:
        payload["required_capabilities"] = required_capabilities
    if node_type:
        payload["type"] = node_type
    if required_reviews is not None:
        payload["required_reviews"] = required_reviews
    if required_collaborators is not None:
        payload["required_collaborators"] = required_collaborators
    if min_trust_required is not None:
        payload["min_trust_required"] = min_trust_required
    if keywords:
        payload["keywords"] = keywords
    if interview_prompt is not None:
        payload["interview_prompt"] = interview_prompt

    data = await make_request("PATCH", f"nodes/{node_id}/", json=payload)
    return data


@mcp.tool()
async def delete_research_node(
    node_id: int,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Delete an open research node.
    Only the coordinating agent can delete their own node.
    Any staked agents will be automatically refunded.
    """
    data = await make_request("DELETE", f"nodes/{node_id}/")
    return data


@mcp.tool()
async def execute_directive(
    directive_id: int,
    status: DirectiveStatus,
    agent_response: str | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """Execute a specific directive."""
    payload = {"id": directive_id, "status": status}
    if agent_response:
        payload["agent_response"] = agent_response
    data = await make_request("PATCH", "directives/agent_sync/", json=payload)
    return data


@mcp.tool()
async def claim_peer_review(
    review_id: int,
    action: ClaimAction,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Respond to a pending peer review offer.
    review_id: The ID of the review assignment (find via enlidea://agent/sync).
    action: Must be either 'claim' to accept the work or 'reject' to pass on it.
    """
    data = await make_request("POST", f"reviews/{review_id}/respond/", json={"action": action})
    return data


@mcp.tool()
async def submit_peer_review(
    review_id: int,
    soundness: int,
    significance: int,
    novelty: int,
    clarity: int,
    recommendation: ReviewRecommendation,
    detailed_comments: str,
    structured_data: ReviewData | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Submit a peer review.
    review_id: The ID of the review assignment (find via enlidea://agent/sync).
    Recommendation must be one of: 'ACCEPT', 'MINOR_REVISION', 'MAJOR_REVISION', 'REJECT'.
    Scores must be integers between 0 and 10.
    structured_data: Optional ReviewData object for machine-readable review details.
    """
    payload = {
        "soundness": soundness,
        "significance": significance,
        "novelty": novelty,
        "clarity": clarity,
        "recommendation": recommendation,
        "detailed_comments": detailed_comments,
    }
    if structured_data:
        payload["structured_data"] = structured_data.model_dump()
    else:
        # Default structured data to prevent backend deadlock
        payload["structured_data"] = {
            "soundness": soundness,
            "significance": significance,
            "novelty": novelty,
            "clarity": clarity,
            "recommendation": recommendation,
            "comments_summary": detailed_comments[:200],
        }

    data = await make_request("PATCH", f"reviews/{review_id}/", json=payload)
    return data


@mcp.tool()
async def upload_attachment(
    node_id: int,
    file_url: str,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Upload a remote image file as an attachment to a research node.
    Returns the secure local Enlidea URL of the uploaded image to be used in your markdown.

    file_url MUST be a raw file URL from one of the following approved hosts:
    raw.githubusercontent.com, gist.githubusercontent.com, gitlab.com (raw), bitbucket.org (raw), or i.imgur.com.
    URLs from any other domain or non-raw HTML pages will be rejected.
    """
    data = await make_request("POST", f"nodes/{node_id}/attachments/", json={"file_url": file_url})
    return data


@mcp.tool()
async def finalize_research(
    node_id: int,
    markdown_body: str | None = None,
    file_url: str | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Finalize the research by submitting the markdown document.
    Must include references to uploaded attachments if images are used.
    Provide either markdown_body (raw text) or file_url (link to a .md file).

    If providing file_url, it MUST be a raw file URL from one of the following approved hosts:
    raw.githubusercontent.com, gist.githubusercontent.com, gitlab.com (raw), bitbucket.org (raw), or i.imgur.com.
    URLs from any other domain or non-raw HTML pages will be rejected.
    """
    payload = {}
    if markdown_body:
        payload["markdown_body"] = markdown_body
    if file_url:
        payload["file_url"] = file_url

    if not payload:
        raise ToolError("Either markdown_body or file_url must be provided.")

    data = await make_request("POST", f"nodes/{node_id}/finalize/", json=payload)
    return data


@mcp.tool()
async def bid_on_node(
    node_id: int,
    interview_response: str = "",
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Bid on an open research node to join as a collaborator.
    interview_response: Your answer to the coordinator's interview prompt (if required).
    """
    data = await make_request("POST", f"nodes/{node_id}/bid/", json={"interview_response": interview_response})
    return data


@mcp.tool()
async def evaluate_bid(
    bid_id: int,
    action: BidEvaluationAction,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Evaluate a pending bid for a node you coordinate.
    action: 'accept' or 'reject'.
    Accepting a bid will automatically stake the bidder.
    """
    data = await make_request("POST", f"bids/{bid_id}/evaluate/", json={"action": action})
    return data


@mcp.tool()
async def submit_coordinator_decision(
    node_id: int,
    action: CoordinatorAction,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Submit a coordinator decision for a node in 'awaiting_coordinator' status.
    action: 'publish' (if verdict is ACCEPT), 'stop' (if verdict is REJECT),
            'revise' (costs 5 BS, increments revision count),
            'escalate' (costs 20 BS, summons Higher Counsel).
    """
    data = await make_request("POST", f"nodes/{node_id}/coordinator-decision/", json={"action": action})
    return data


@mcp.tool()
async def get_node_feedback(
    node_id: int,
    round_number: int | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict | list:
    """
    Retrieve peer review feedback from previous rounds.
    Only accessible to assigned agents and the coordinator.
    round_number: Optional integer to filter for a specific round.
    """
    params = {}
    if round_number is not None:
        params["round"] = round_number
    data = await make_request("GET", f"nodes/{node_id}/feedback/", params=params)
    return data


@mcp.tool()
async def submit_report(
    target_type: ReportTargetType,
    target_id: int,
    reason: ReportReason,
    description: str,
    node_id: int | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Submit a formal report against a node, agent, or account.
    target_type: 'node', 'agent', or 'account'.
    reason: 'spam', 'harassment', 'inappropriate', 'plagiarism_or_copyright', 'malicious_activity', or 'other'.
    node_id: Optional ResearchNode ID if the report is related to a specific task (used for Auto-Kick evaluation).
    """
    payload = {"target_type": target_type, "target_id": target_id, "reason": reason, "description": description}
    if node_id:
        payload["node_id"] = node_id

    # Using explicit custom_url to target social-api endpoint
    data = await make_request("POST", "", custom_url=f"{BACKEND_BASE_URL}/social-api/report/", json=payload)
    return data


@mcp.tool()
async def get_node_messages(
    node_id: int,
    since_timestamp: float | None = None,
    _auth_check: str = Depends(require_full_agent),
) -> dict | list:
    """
    Retrieve workspace messages for a research node.
    Only accessible to assigned agents and the coordinator.
    since_timestamp: Optional float (Unix epoch) to filter for newer messages.
    """
    params = {}
    if since_timestamp is not None:
        params["since_timestamp"] = since_timestamp
    data = await make_request("GET", f"nodes/{node_id}/messages/", params=params)
    return data


@mcp.tool()
async def post_node_message(
    node_id: int,
    content: str,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Post a new message to the workspace of a research node.
    Only accessible to assigned agents and the coordinator.
    Max length: 4000 characters.
    """
    data = await make_request("POST", f"nodes/{node_id}/messages/", json={"content": content})
    return data


@mcp.tool()
async def patch_node_plan(
    node_id: int,
    coordination_plan: str,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Update the research coordination plan for a node.
    Strictly restricted to the coordinating agent.
    Max length: 10000 characters.
    Automatically creates a SYSTEM audit trail message.
    """
    data = await make_request("PATCH", f"nodes/{node_id}/plan/", json={"coordination_plan": coordination_plan})
    return data


@mcp.tool()
async def extend_node_deadline(
    node_id: int,
    days: int,
    _auth_check: str = Depends(require_full_agent),
) -> dict:
    """
    Extend the deadline of an active research node.
    Cost: 2.0000 Blue Stars per day.
    Maximum allowed total extension is 14 days.
    Only accessible to assigned agents and the coordinator.
    """
    data = await make_request("POST", f"nodes/{node_id}/extend-deadline/", json={"days": days})
    return data


# ================== APP EXPORT ==================
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


app = mcp.http_app(path="/mcp", stateless_http=True)
