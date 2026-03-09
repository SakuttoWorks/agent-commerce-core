import hashlib
import logging
import os

# Use the structured logger configuration from the main application
logger = logging.getLogger("agent-commerce-core.guardian")

class BudgetGuardian:
    """
    Resilient Cost-Control & Caching Layer.
    
    Operates in 'Stateless Mode' using volatile memory when Redis is unreachable.
    Designed for Cloud Run v2 container lifecycles to ensure budget safety 
    without external dependencies during cold starts.
    """
    
    # Class-level volatile memory for stateless container reuse
    _memory_cache = {}
    _daily_usage = 0

    def __init__(self):
        # Default safety limit: 50 queries per container instance
        self.DAILY_SEARCH_LIMIT = int(os.getenv("DAILY_SEARCH_LIMIT", "50"))
        # Soft limit mode allows traffic analysis even after budget breach (for calibration)
        self.STRICT_ENFORCEMENT = os.getenv("STRICT_BUDGET_MODE", "false").lower() == "true"
        self.CACHE_TTL = 86400

    def _get_cache_key(self, query: str):
        """Generates a SHA-256 hash key for semantic caching."""
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return f"cache:search:{query_hash}"

    def check_cache(self, query: str):
        """Retrieves result from volatile memory if available."""
        key = self._get_cache_key(query)
        data = self._memory_cache.get(key)
        
        if data:
            logger.info(f"⚡ Cache Hit (Volatile Memory). Query: {query[:20]}...")
            return data
        return None

    def save_cache(self, query: str, result: dict):
        """Persists search results to volatile memory for short-term reuse."""
        try:
            key = self._get_cache_key(query)
            self._memory_cache[key] = result
        except Exception as e:
            logger.error(f"Cache write failure: {e}")

    def check_budget_and_increment(self):
        """
        Circuit Breaker for Cost Control.
        Monitors usage against daily limits defined in environment variables.
        """
        try:
            # Check current consumption
            if self._daily_usage >= self.DAILY_SEARCH_LIMIT:
                logger.warning(
                    f"⚠️ Budget Soft-Limit Reached! ({self._daily_usage}/{self.DAILY_SEARCH_LIMIT})"
                )
                
                # In strict mode, block the request. 
                # Otherwise, allow it for system calibration (Phase 1 behavior).
                if self.STRICT_ENFORCEMENT:
                    return False
                
                logger.info("Proceeding under Soft-Limit protocols (Calibration Mode).")
                return True 

            # Increment atomic counter (not thread-safe in Python, but sufficient for single worker)
            self._daily_usage += 1
            logger.info(f"Budget Check Passed. Usage: {self._daily_usage}/{self.DAILY_SEARCH_LIMIT}")
            return True

        except Exception as e:
            logger.error(f"Budget circuit breaker error: {e}")
            # Fail open to maintain service availability during error
            return True
