import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

# --- Cleaned Project Imports ---
from app.models.schemas import (
    AgentSemanticError,
    AsyncJobResponse,
    NormalizeRequest,
    NormalizeResponse,
)
from app.tools.gemini_normalizer import normalizer
from app.tools.web_search import search_web
from app.utils.guardian import data_guardian, verify_gateway
from app.utils.trust_metrics import calculate_hybrid_trust_score


# --- 1. Environment & Structured Logging ---
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
    version="4.0.0",
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
    """Translates standard HTTP errors into AI-friendly Semantic Errors with resilient headers."""
    error_type = "api_error"
    instruction = "Please review your request parameters and try again."
    trace_id = request.headers.get("X-Trace-Id", "unknown-trace-id")

    if exc.status_code == 400:
        error_type = "bad_request"
        instruction = "Your input was invalid. Ensure the payload format is correct."
    elif exc.status_code == 403:
        error_type = "compliance_violation"
        instruction = (
            "CRITICAL: Prohibited request. Halt this inquiry and change your approach."
        )
    elif exc.status_code == 404:
        error_type = "not_found"
        instruction = (
            "The requested resource was not found. Please verify the target URL."
        )
    elif exc.status_code == 429:
        error_type = "rate_limit_exceeded"
        instruction = "Wait for at least 60 seconds (Retry-After) before attempting another request."

    if isinstance(exc.detail, dict) and "error_type" in exc.detail:
        semantic_error = AgentSemanticError(**exc.detail)
    else:
        semantic_error = AgentSemanticError(
            error_type=error_type,
            message=str(exc.detail),
            agent_instruction=instruction,
        )

    headers = exc.headers if exc.headers else {}
    if exc.status_code == 429 and "Retry-After" not in headers:
        headers["Retry-After"] = "60"

    response_content = semantic_error.model_dump()
    response_content["trace_id"] = trace_id

    return JSONResponse(
        status_code=exc.status_code,
        content=response_content,
        headers=headers,
    )


@app.exception_handler(RequestValidationError)
async def semantic_validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    trace_id = request.headers.get("X-Trace-Id", "unknown-trace-id")
    semantic_error = AgentSemanticError(
        error_type="schema_mismatch",
        message=f"Invalid payload structure: {exc.errors()}",
        agent_instruction="Correct your JSON payload to match the expected schema (url, format_type) before retrying.",
    )
    response_content = semantic_error.model_dump()
    response_content["trace_id"] = trace_id

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=response_content,
    )


# --- 4. Network Security & Reachability Module ---
async def verify_url_is_live(url: str):
    """Validates if the target URL is reachable before delegating to extraction APIs."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(verify=False, headers=headers) as client:
            response = await client.head(url, follow_redirects=True, timeout=10.0)
            if response.status_code >= 400:
                response = await client.get(url, follow_redirects=True, timeout=10.0)
                if response.status_code >= 400:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error_type": "unreachable_url",
                            "message": f"Target URL returned HTTP {response.status_code}. It is offline or blocking access.",
                            "agent_instruction": f"CRITICAL: The requested URL ({url}) is inaccessible. Do not attempt to process it or hallucinate data.",
                        },
                    )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_type": "dns_or_network_error",
                "message": f"Network error when verifying URL: {str(e)}",
                "agent_instruction": "CRITICAL: DNS resolution or network connection failed for this URL. The domain does not exist or is unreachable.",
            },
        )


# --- 5. Advanced Extraction Modules ---
async def extract_via_jina(url: str) -> str | None:
    jina_key = os.getenv("JINA_API_KEY")
    if not jina_key:
        return None
    headers = {"Authorization": f"Bearer {jina_key}", "X-Return-Format": "markdown"}
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


# --- 6. Core Logic Pipeline (Separated for Sync/Async reuse) ---
async def execute_normalization_pipeline(
    request: NormalizeRequest, tenant_id: str, fields: str | None
) -> NormalizeResponse:
    """Executes the core fallback strategy and normalization logic."""
    data_guardian.enforce_compliance(request.url)
    await verify_url_is_live(request.url)

    combined_raw_text = ""
    fetched_at = None
    extraction_route = "unknown"

    logger.info("Attempting extraction via Jina Reader...")
    jina_text = await extract_via_jina(request.url)
    if jina_text:
        combined_raw_text = f"Source: {request.url}\nContent: {jina_text}"
        extraction_route = "jina"

    if not combined_raw_text.strip():
        logger.info("Jina failed or skipped. Attempting Firecrawl...")
        firecrawl_text = await extract_via_firecrawl(request.url)
        if firecrawl_text:
            combined_raw_text = f"Source: {request.url}\nContent: {firecrawl_text}"
            extraction_route = "firecrawl"

    if not combined_raw_text.strip():
        logger.info("Extraction APIs failed. Falling back to Tavily Web Search...")
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
            fetched_at = search_result.get("fetched_at")
            extraction_route = "search"
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Search failure: {e}")
            raise HTTPException(status_code=500, detail="Internal Search Engine Error")

    if not combined_raw_text.strip():
        raise HTTPException(
            status_code=404, detail="No extractable content found for the provided URL."
        )

    data_guardian.enforce_compliance(combined_raw_text)

    success, extracted_data, meta = normalizer.normalize(
        raw_text=combined_raw_text,
        format_type=request.format_type,
        use_pro_model=False,
        requested_fields=fields,
        target_tier=request.target_tier,
    )

    if not success:
        status_code = meta.get("status_code", 500)
        error_msg = meta.get("error", "AI Normalization failed")
        if status_code == 429:
            raise HTTPException(
                status_code=429,
                detail={
                    "error_type": "rate_limit_exceeded",
                    "message": "The upstream AI provider is currently out of quota.",
                    "agent_instruction": "CRITICAL: Rate limit exceeded. Wait 60 seconds before retrying.",
                },
            )
        raise HTTPException(status_code=status_code, detail=error_msg)

    if fields and isinstance(extracted_data, str):
        try:
            parsed_data = json.loads(extracted_data)
            requested_keys = [key.strip() for key in fields.split(",") if key.strip()]
            if requested_keys and isinstance(parsed_data, dict):
                filtered_data = {
                    k: v for k, v in parsed_data.items() if k in requested_keys
                }
                extracted_data = filtered_data if filtered_data else parsed_data
            else:
                extracted_data = parsed_data
        except json.JSONDecodeError:
            pass

    freshness_seconds = None
    if fetched_at:
        try:
            fetched_time = datetime.fromisoformat(fetched_at)
            freshness_seconds = int(
                (datetime.now(timezone.utc) - fetched_time).total_seconds()
            )
            meta["X-Data-Freshness-Seconds"] = freshness_seconds
        except ValueError:
            meta["X-Data-Freshness"] = fetched_at

    meta["extraction_route"] = extraction_route
    llm_trust_score = meta.pop("trust_score", 1.0)
    final_hybrid_score = calculate_hybrid_trust_score(
        llm_score=llm_trust_score,
        extraction_route=extraction_route,
        data_freshness_seconds=freshness_seconds,
    )

    current_timestamp = datetime.now(timezone.utc).isoformat()
    return NormalizeResponse(
        success=True,
        data=extracted_data,
        source_url=request.url,
        timestamp=current_timestamp,
        trust_score=final_hybrid_score,
        metadata=meta,
    )


# --- 7. Async Background Worker ---
async def dispatch_webhook_payload(
    job_id: str,
    request: NormalizeRequest,
    tenant_id: str,
    trace_id: str,
    fields: str | None,
):
    """Executes the pipeline in the background and POSTs the result to the webhook URL."""
    webhook_url = request.webhook.url
    headers = {"Content-Type": "application/json"}
    if request.webhook.secret_token:
        headers["Authorization"] = f"Bearer {request.webhook.secret_token}"

    try:
        result = await execute_normalization_pipeline(request, tenant_id, fields)
        payload = result.model_dump()
        payload["job_id"] = job_id
        payload["trace_id"] = trace_id
    except HTTPException as e:
        logger.error(f"Async Job {job_id} failed with HTTP exception: {e.detail}")
        payload = {
            "success": False,
            "job_id": job_id,
            "error": e.detail,
            "trace_id": trace_id,
        }
    except Exception as e:
        logger.error(f"Async Job {job_id} failed with unexpected error: {e}")
        payload = {
            "success": False,
            "job_id": job_id,
            "error": str(e),
            "trace_id": trace_id,
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url, json=payload, headers=headers, timeout=30.0
            )
            if response.status_code >= 400:
                logger.warning(
                    f"Failed to deliver webhook for job {job_id}. Status: {response.status_code}"
                )
            else:
                logger.info(f"Successfully delivered webhook for job {job_id}.")
    except Exception as network_err:
        logger.error(
            f"Webhook delivery failed for job {job_id} due to network error: {network_err}"
        )


# --- 8. API Endpoints ---
@app.get("/")
async def health_check():
    return {
        "status": "online",
        "service": "Agent-Commerce-OS Layer B",
        "version": "4.0.0",
    }


@app.post("/v1/normalize_web_data")
async def normalize_web_data_endpoint(
    request: NormalizeRequest,
    background_tasks: BackgroundTasks,
    gateway_data: dict = Depends(verify_gateway),
    fields: str | None = Query(
        default=None, description="Comma-separated fields to extract (Lite GraphQL)"
    ),
):
    """
    The Main Normalization Pipeline. Supports synchronous responses or Async Webhooks.
    """
    tenant_id = gateway_data["tenant_id"]
    trace_id = gateway_data["trace_id"]

    logger.info(
        f"Processing normalization request for tenant: {tenant_id}, trace: {trace_id}, URL: {request.url}, tier: {request.target_tier}"
    )

    if request.webhook and request.webhook.url:
        job_id = f"job_{uuid.uuid4().hex}"
        background_tasks.add_task(
            dispatch_webhook_payload, job_id, request, tenant_id, trace_id, fields
        )

        response_payload = AsyncJobResponse(
            success=True,
            job_id=job_id,
            message=f"Job queued successfully. Results will be posted to {request.webhook.url}",
        ).model_dump()
        response_payload["trace_id"] = trace_id

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=response_payload,
        )

    result = await execute_normalization_pipeline(request, tenant_id, fields)
    response_payload = result.model_dump()
    response_payload["trace_id"] = trace_id

    return JSONResponse(status_code=status.HTTP_200_OK, content=response_payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
