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
# 2. Input/Request Models (Matches Layer C MCP / Layer A Gateway)
# ==========================================
class NormalizeRequest(BaseModel):
    """
    Payload for the primary normalization and extraction engine.
    Must perfectly match the inputSchema defined in Layer C's MCP endpoint and forwarded by Layer A's Gateway.

    Note: 'fields' (Lite GraphQL feature) is handled dynamically as a query parameter
    in the FastAPI endpoint routing, and thus is intentionally excluded from this body schema.
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


# ==========================================
# 3. Output/Response Models
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
