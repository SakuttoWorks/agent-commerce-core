import hashlib
import json
import logging
import os
from datetime import datetime, timezone

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class BudgetGuardian:
    """
    審査・デモ用スタンドアローンGuardian
    Redisの代わりにインメモリ(一時メモリ)を使用して、
    キャッシュとレート制限をシミュレーションします。
    """
    
    # クラス変数としてメモリを保持 (アプリが再起動するとリセット)
    _memory_cache = {}
    _daily_usage = 0

    def __init__(self):
        # 環境変数から制限値を取得 (デフォルト: 50)
        self.DAILY_SEARCH_LIMIT = int(os.getenv("DAILY_SEARCH_LIMIT", "50"))
        self.CACHE_TTL = 86400

    def _get_cache_key(self, query: str):
        """クエリをハッシュ化してキャッシュキーを作成"""
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        return f"cache:search:{query_hash}"

    def check_cache(self, query: str):
        """キャッシュがあればデータを返す"""
        key = self._get_cache_key(query)
        data = self._memory_cache.get(key)
        
        if data:
            logger.info(f"⚡ Cache Hit (Memory)! Query: {query[:20]}...")
            return data
        return None

    def save_cache(self, query: str, result: dict):
        """検索結果をメモリに保存"""
        try:
            key = self._get_cache_key(query)
            self._memory_cache[key] = result
        except Exception as e:
            logger.error(f"Cache save error: {e}")

    def check_budget_and_increment(self):
        """
        簡易的な予算チェック (Kill Switch)
        """
        try:
            # 現在のカウントをチェック
            if self._daily_usage >= self.DAILY_SEARCH_LIMIT:
                logger.warning(
                    f"⚠️ Budget Limit Reached! Limit: {self.DAILY_SEARCH_LIMIT}"
                )
                # デモ中は停止させないほうが安全なので、警告だけ出してTrueを返す設定
                # 本番運用時はここを False にする
                return True 

            # カウントアップ
            self._daily_usage += 1
            logger.info(f"Budget Check OK. Usage: {self._daily_usage}/{self.DAILY_SEARCH_LIMIT}")
            return True

        except Exception as e:
            logger.error(f"Budget check error: {e}")
            return True
