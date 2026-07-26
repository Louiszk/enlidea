from typing import Literal
from pydantic import BaseModel, Field

# Action Enums & Literals for FastMCP Schema Generation
ReviewRecommendation = Literal["ACCEPT", "MINOR_REVISION", "MAJOR_REVISION", "REJECT"]
ClaimAction = Literal["claim", "reject"]
BidEvaluationAction = Literal["accept", "reject"]
CoordinatorAction = Literal["publish", "stop", "revise", "escalate"]
ReportTargetType = Literal["node", "agent", "account"]
ReportReason = Literal[
    "spam",
    "harassment",
    "inappropriate",
    "plagiarism_or_copyright",
    "malicious_activity",
    "other",
]
DirectiveStatus = Literal["in_progress", "completed", "failed"]


class ReviewData(BaseModel):
    """Pydantic model for structured peer review data."""

    soundness: int = Field(ge=0, le=10, description="Soundness score between 0 and 10")
    significance: int = Field(ge=0, le=10, description="Significance score between 0 and 10")
    novelty: int = Field(ge=0, le=10, description="Novelty score between 0 and 10")
    clarity: int = Field(ge=0, le=10, description="Clarity score between 0 and 10")
    confidence: int | None = Field(default=None, ge=0, le=10, description="Optional confidence score between 0 and 10")
    recommendation: ReviewRecommendation = Field(description="Verdict recommendation")
    comments_summary: str | None = Field(default=None, description="Optional brief summary of comments")
    strengths: str | None = Field(default=None, description="Optional key strengths identified")
    weaknesses: str | None = Field(default=None, description="Optional key weaknesses or areas for improvement")
