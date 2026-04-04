from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ==========================================
# 1. Semantic Error Handling Models (AEO)
# ==========================================
class AgentSemanticError(BaseModel):
    """
    Structured error response designed specifically for AI Agents to self-correct.
    """

    error_type: str = Field(
        ...,
        description="Machine-readable error category (e.g., 'compliance_violation', 'quota_exceeded', 'schema_mismatch').",
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
    """

    url: str = Field(
        ..., description="The target public URL to fetch and normalize data from."
    )
    format_type: str = Field(
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
    data: str = Field(
        ...,
        description="The extracted and normalized content in the requested format (Markdown string or JSON string).",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional metadata about the extraction (e.g., token usage, processing time, source title).",
    )
