import os

# さきほど移動したGuardianをインポート
from app.utils.guardian import BudgetGuardian
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

# Guardianのインスタンス化 (キャッシュと予算管理)
guardian = BudgetGuardian()

# ツール定義
TAVILY_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_web",
        # 修正箇所: 「株価」を削除し、「公共データ」や「ドキュメント」に変更
        "description": "Web上の公開情報を検索・取得します。技術ドキュメント、自治体情報、ニュースなど。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "検索したいキーワードや質問文",
                }
            },
            "required": ["query"],
        },
    },
}


def search_web(query: str):
    """
    Tavily APIを実行する関数 (Guardianによる保護付き)
    """
    # 1. キャッシュチェック (お金の節約)
    cached_result = guardian.check_cache(query)
    if cached_result:
        return f"(Cache Hit) {cached_result}"

    # 2. 予算(Kill Switch)チェック
    if not guardian.check_budget_and_increment():
        return "Error: Daily search budget exceeded. Please try again tomorrow."

    # 3. API実行
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found."

    try:
        client = TavilyClient(api_key=api_key)
        # qna_search=True: AI向けの回答生成モード
        result = client.qna_search(query=query)

        # 4. 結果をキャッシュに保存
        guardian.save_cache(query, result)

        return result
    except Exception as e:
        return f"Search Error: {str(e)}"
