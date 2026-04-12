from typing import Annotated, Any

from pydantic import BaseModel, Field, StringConstraints


# ==========================================
# 1. Semantic Error Handling Models (AEO)
# ==========================================
class AgentSemanticError(BaseModel):
    """
    Structured error response designed specifically for AI Agents to self-correct.
    """

    error_type: str = Field(
        ...,
        description="Machine-readable error category (e.g., 'compliance_violation', 'rate_limit_exceeded', 'unreachable_url', 'schema_mismatch').",
    )
    message: str = Field(..., description="Detailed description of what went wrong.")
    agent_instruction: str = Field(
        ...,
        description="CRITICAL: Explicit instruction for the AI agent on how to alter its prompt, change its tool usage, or gracefully terminate the task to recover from this error.",
    )


# ==========================================
# 2. Webhook & Async Task Models
# ==========================================
class WebhookConfig(BaseModel):
    """Configuration for asynchronous webhook delivery."""

    url: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ...,
        description="The secure HTTPS endpoint to receive the normalized payload upon completion.",
    )
    secret_token: str | None = Field(
        default=None,
        description="Optional bearer token for webhook endpoint authentication.",
    )


class AsyncJobResponse(BaseModel):
    """Immediate response returned when a webhook configuration is provided."""

    success: bool = Field(
        default=True, description="Indicates the job was successfully queued."
    )
    job_id: str = Field(
        ..., description="Unique identifier for the background extraction task."
    )
    message: str = Field(..., description="Status message explaining the async flow.")


# ==========================================
# 3. Input/Request Models (Matches Layer C MCP / Layer A Gateway)
# ==========================================
class NormalizeRequest(BaseModel):
    """
    Payload for the primary normalization and extraction engine.
    Must perfectly match the inputSchema defined in Layer C's MCP endpoint and forwarded by Layer A's Gateway.
    """

    url: Annotated[str, StringConstraints(strip_whitespace=True)] = Field(
        ..., description="The target public URL to fetch and normalize data from."
    )
    format_type: Annotated[
        str, StringConstraints(strip_whitespace=True, to_lower=True)
    ] = Field(
        default="markdown",
        description="Desired output format. Supported values: 'json', 'markdown'.",
    )
    target_tier: str = Field(
        default="standard",
        description="Specifies the extraction tier. Options: 'standard', 'tier_a1' (deep research), 'tier_a2' (actionable), 'tier_a3' (compliance).",
    )
    webhook: WebhookConfig | None = Field(
        default=None,
        description="Optional: Provide this configuration to trigger asynchronous processing. A Job ID will be returned immediately, and results will be POSTed to the webhook URL.",
    )


# ==========================================
# 4. Output/Response Models
# ==========================================
class NormalizeResponse(BaseModel):
    """
    Standard successful response containing the normalized data.
    """

    success: bool = Field(
        default=True, description="Indicates if the normalization was successful."
    )
    data: Any = Field(
        ...,
        description="The extracted and normalized content. Can be a Markdown string, a complete JSON object (dict), or a dynamically filtered subset of fields (Lite GraphQL).",
    )
    source_url: str | None = Field(
        default=None, description="The verified source URL of the extracted data."
    )
    timestamp: str | None = Field(
        default=None, description="Absolute ISO-8601 timestamp of the extraction."
    )
    trust_score: float | None = Field(
        default=None,
        description="Automated LLM-generated confidence/trust score (0.0 to 1.0) based on extraction fidelity and hallucination absence.",
    )
    metadata: dict[str, Any] | None = Field(
        default_factory=dict,
        description="Optional metadata about the extraction (e.g., token usage, processing time, source title).",
    )
