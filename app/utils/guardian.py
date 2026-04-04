import logging
import os
import re
import urllib.parse

from fastapi import Header, HTTPException, status

logger = logging.getLogger("agent-commerce-core.guardian")

# ==========================================
# 1. Zero Trust Security (Gateway Authentication)
# ==========================================
INTERNAL_SECRET = os.getenv("INTERNAL_AUTH_SECRET", "")


async def verify_gateway(
    x_internal_secret: str = Header(
        ..., description="Strictly required secret token from Layer A (Gateway)."
    ),
    x_tenant_id: str = Header(
        ..., description="SHA-256 hashed Tenant ID passed from Layer A."
    ),
) -> str:
    """
    FastAPI Dependency: Ensures the request is genuinely routed through Layer A.
    Returns the tenant_id for logging/isolation purposes if successful.
    """
    if x_internal_secret != INTERNAL_SECRET:
        logger.critical(
            f"🚨 SECURITY BREACH ATTEMPT: Invalid internal secret from Tenant {x_tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid internal gateway secret. Direct access to Layer B is prohibited.",
        )

    return x_tenant_id


# ==========================================
# 2. Strict Compliance Guard (Defense in Depth)
# ==========================================
class DataGuardian:
    """
    Ensures absolute compliance with the "No Financial/Trading" strict rule.
    """

    FORBIDDEN_KEYWORDS = [
        "market analysis",
        "financial intelligence",
        "trading signal",
        "investment",
        "stock price",
        "crypto",
        "forex",
        "dividend",
        "portfolio",
        "buy signal",
        "sell signal",
        "price prediction",
        "arbitrage",
        "day trading",
        "cryptocurrency",
        "trading",
        "finance",
        "market trend",
        "crypto asset",
        "chart analysis",
        "profit prediction",
    ]

    def __init__(self):
        pattern = "|".join(map(re.escape, self.FORBIDDEN_KEYWORDS))
        self.compliance_regex = re.compile(f"({pattern})", re.IGNORECASE)

    def enforce_compliance(self, text: str) -> None:
        """
        Validates the text against the strict non-financial policy.
        Raises an HTTPException specifically formatted for AI Agent self-correction.
        """
        if not text or not str(text).strip():
            return

        # 🚨 FIX: Decode strings in case AI sends URL-encoded text
        decoded_text = urllib.parse.unquote(str(text))

        match = self.compliance_regex.search(decoded_text)
        if match:
            forbidden_term = match.group(1)
            logger.warning(
                f"🚨 COMPLIANCE BLOCK: Forbidden term detected: '{forbidden_term}'"
            )

            # Formatting error to match AgentSemanticError schema
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_type": "compliance_violation",
                    "message": f"Request blocked due to compliance policy. Forbidden term: '{forbidden_term}'",
                    "agent_instruction": "CRITICAL: This infrastructure is strictly for standard data normalization. Financial analysis, trading, and investment-related queries are strictly prohibited. Alter your prompt and remove financial terms.",
                },
            )


# Singleton instance for use across the application
data_guardian = DataGuardian()
