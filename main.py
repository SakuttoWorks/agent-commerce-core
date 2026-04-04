import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

# --- Cleaned Project Imports ---
from app.models.schemas import AgentSemanticError, NormalizeRequest, NormalizeResponse
from app.tools.gemini_normalizer import normalizer
from app.tools.web_search import search_web
from app.utils.guardian import data_guardian, verify_gateway
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# --- 1. Environment & Structured Logging ---
load_dotenv()


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "severity": record.levelname,
            "time": datetime.now(timezone.utc).isoformat(),
            "message": record.getMessage(),
            "module": record.module,
        }
        return json.dumps(log_obj)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)
logger = logging.getLogger("agent-commerce-core.main")

# --- 2. Application Definition ---
app = FastAPI(
    title="Agent-Commerce-OS Core",
    description="Layer B: High-performance Data Normalization Engine (Stateless)",
    version="3.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 3. Semantic Error Handlers (AEO) ---
@app.exception_handler(HTTPException)
async def semantic_http_exception_handler(request: Request, exc: HTTPException):
    """Translates standard HTTP errors into AI-friendly Semantic Errors."""
    error_type = "api_error"
    instruction = "Please review your request parameters and try again."

    if exc.status_code == 400:
        error_type = "bad_request"
        instruction = "Your input was invalid. Ensure payload is correct."
    elif exc.status_code == 403:
        error_type = "compliance_violation"
        instruction = (
            "CRITICAL: Prohibited request. Halt this inquiry and change your approach."
        )

    # Check if the detail is already structured as our AgentSemanticError payload
    if isinstance(exc.detail, dict) and "error_type" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)

    semantic_error = AgentSemanticError(
        error_type=error_type, message=str(exc.detail), agent_instruction=instruction
    )
    return JSONResponse(
        status_code=exc.status_code, content=semantic_error.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def semantic_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    semantic_error = AgentSemanticError(
        error_type="schema_mismatch",
        message=f"Invalid payload structure: {exc.errors()}",
        agent_instruction="Correct your JSON payload to match the expected schema (url, format_type) before retrying.",
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=semantic_error.model_dump(),
    )


# --- 4. Advanced Extraction Modules ---
async def extract_via_jina(url: str) -> str | None:
    """Uses Jina Reader API for ultra-fast, LLM-optimized Markdown extraction."""
    jina_key = os.getenv("JINA_API_KEY")
    if not jina_key:
        return None

    headers = {"Authorization": f"Bearer {jina_key}"}
    headers["X-Return-Format"] = "markdown"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://r.jina.ai/{url}", headers=headers, timeout=30.0
            )
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(
                    f"Jina Reader failed with status {response.status_code}."
                )
    except Exception as e:
        logger.error(f"Jina Reader extraction error: {e}")
    return None


async def extract_via_firecrawl(url: str) -> str | None:
    """Uses Firecrawl API as a robust secondary scraper if Jina fails."""
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    if not firecrawl_key:
        return None

    headers = {
        "Authorization": f"Bearer {firecrawl_key}",
        "Content-Type": "application/json",
    }
    payload = {"url": url, "formats": ["markdown"]}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers=headers,
                json=payload,
                timeout=45.0,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return data.get("data", {}).get("markdown")
            logger.warning(f"Firecrawl failed with status {response.status_code}.")
    except Exception as e:
        logger.error(f"Firecrawl extraction error: {e}")
    return None


# --- 5. API Endpoints ---
@app.get("/")
async def health_check():
    return {
        "status": "online",
        "service": "Agent-Commerce-OS Layer B",
        "version": "3.0.0",
    }


@app.post("/v1/normalize_web_data", response_model=NormalizeResponse)
async def normalize_web_data_endpoint(
    request: NormalizeRequest,
    tenant_id: str = Depends(verify_gateway),  # Zero-Trust Security Gateway
):
    """
    [CRITICAL TASK 2 & 3] The Main Normalization Pipeline.
    Implements a fallback strategy: Jina Reader -> Firecrawl -> Tavily.
    """
    logger.info(
        f"Processing normalization request for tenant: {tenant_id}, URL: {request.url}"
    )

    # 1. Compliance Check (Fail fast if prohibited terms are found)
    data_guardian.enforce_compliance(request.url)

    combined_raw_text = ""
    fetched_at = None

    # 2. Strategy A: Try Jina Reader first (Fastest, best for single pages)
    logger.info("Attempting extraction via Jina Reader...")
    jina_text = await extract_via_jina(request.url)
    if jina_text:
        combined_raw_text = f"Source: {request.url}\nContent: {jina_text}"

    # 3. Strategy B: Fallback to Firecrawl (Robust scraping)
    if not combined_raw_text.strip():
        logger.info("Jina failed or skipped. Attempting Firecrawl...")
        firecrawl_text = await extract_via_firecrawl(request.url)
        if firecrawl_text:
            combined_raw_text = f"Source: {request.url}\nContent: {firecrawl_text}"

    # 4. Strategy C: Fallback to Tavily (Web Search Engine)
    if not combined_raw_text.strip():
        logger.info(
            "Extraction APIs failed or skipped. Falling back to Tavily Web Search..."
        )
        search_json_str = search_web(request.url)
        try:
            search_result = json.loads(search_json_str)
            if search_result.get("status") == "error":
                raise HTTPException(
                    status_code=500, detail=search_result.get("message")
                )

            results = search_result.get("results", [])
            combined_raw_text = "\n\n".join(
                [
                    f"Source: {r.get('url')}\nContent: {r.get('raw_content', '')}"
                    for r in results
                ]
            )
            # Retrieve timestamp for freshness calculation
            fetched_at = search_result.get("fetched_at")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Search failure: {e}")
            raise HTTPException(status_code=500, detail="Internal Search Engine Error")

    if not combined_raw_text.strip():
        raise HTTPException(
            status_code=404, detail="No extractable content found for the provided URL."
        )

    # 5. Gemini Normalization Engine
    # Note: Can be upgraded to use_pro_model=True based on tenant_id tier in the future
    success, extracted_data, meta = normalizer.normalize(
        raw_text=combined_raw_text, format_type=request.format_type, use_pro_model=False
    )

    if not success:
        raise HTTPException(
            status_code=500, detail=meta.get("error", "AI Normalization failed")
        )

    # Calculate Data Freshness if fetched via search
    if fetched_at:
        try:
            fetched_time = datetime.fromisoformat(fetched_at)
            freshness_seconds = int(
                (datetime.now(timezone.utc) - fetched_time).total_seconds()
            )
            meta["X-Data-Freshness-Seconds"] = freshness_seconds
        except ValueError:
            meta["X-Data-Freshness"] = fetched_at

    # 6. Return formatted response (Strictly adheres to NormalizeResponse schema)
    return NormalizeResponse(success=True, data=extracted_data, metadata=meta)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
