import json
import logging
import os
from datetime import datetime, timezone

from tavily import TavilyClient

# Import the newly created compliance gateway
from app.utils.guardian import data_guardian

# Setup logger for this module
logger = logging.getLogger("agent-commerce-core.web_search")


def search_web(query: str) -> str:
    """
    Executes Tavily API Deep Search.
    Returns structured JSON containing raw_content, urls, and a UTC timestamp
    (fetched_at) for upstream X-Data-Freshness-Seconds calculation.
    """
    # 1. Strict Compliance Guard (Kill Switch)
    # If the search query contains financial/investment terms, instantly raise an HTTP 400 error (AgentSemanticError)
    data_guardian.enforce_compliance(query)

    # 2. API Execution setup
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        logger.error("TAVILY_API_KEY not found in environment.")
        return json.dumps(
            {"status": "error", "message": "TAVILY_API_KEY not found in environment."}
        )

    try:
        client = TavilyClient(api_key=api_key)

        # 3. Deep Search Execution
        # Using search_depth="advanced" and extracting raw content for Gemini's processing
        response = client.search(
            query=query,
            search_depth="advanced",
            include_raw_content=True,
            max_results=3,  # Minimized to top 3 to optimize context window & tokens
        )

        extracted_results = []
        if "results" in response:
            for item in response["results"]:
                extracted_results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "summary": item.get("content", ""),
                        "raw_content": item.get(
                            "raw_content", ""
                        ),  # Key component for agent normalization
                    }
                )

        # 4. Embed timestamp for 'X-Data-Freshness-Seconds' calculation in main.py
        payload = {
            "status": "success",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "results": extracted_results,
        }

        return json.dumps(payload, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Tavily Search Engine Error: {str(e)}")
        return json.dumps(
            {"status": "error", "message": f"Tavily Search Engine Error: {str(e)}"}
        )
