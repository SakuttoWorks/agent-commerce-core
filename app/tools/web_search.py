import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Import Guardian for budget and cache control
from app.utils.guardian import BudgetGuardian

load_dotenv()

# Initialize Guardian (Cache & Budget Management)
guardian = BudgetGuardian()

# LLM Function Definition
TAVILY_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_web",
        # Strictly defined scope: Public data extraction and normalization only.
        "description": "Retrieves public web information for data normalization. Targets technical documentation, municipal data, and general news.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search keyword or semantic query string.",
                }
            },
            "required": ["query"],
        },
    },
}


def search_web(query: str):
    """
    Executes Tavily API search with Guardian protection (Budget & Cache).
    """
    # 1. Cache Check (Cost Optimization)
    cached_result = guardian.check_cache(query)
    if cached_result:
        return f"(Cache Hit) {cached_result}"

    # 2. Budget (Kill Switch) Check
    if not guardian.check_budget_and_increment():
        return "Error: Daily search budget exceeded. Limit enforced by Guardian."

    # 3. API Execution
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found."

    try:
        client = TavilyClient(api_key=api_key)
        # qna_search=True: Optimized for RAG context retrieval
        result = client.qna_search(query=query)

        # 4. Save to Cache
        guardian.save_cache(query, result)

        return result
    except Exception as e:
        return f"Search Error: {str(e)}"
