import os
import time

import jwt  # 🚨 修正: 脆弱性のある python-jose から PyJWT に変更
from fastapi import Depends, HTTPException, status
from supabase import Client, ClientOptions, create_client

# 先ほど作成したゼロトラスト関所をインポート
from app.utils.guardian import verify_gateway

# 起動時に環境変数からシークレットを読み込み
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


def get_tenant_db_client(tenant_id: str = Depends(verify_gateway)) -> Client:
    """
    FastAPI Dependency:
    ゼロトラスト関所 (verify_gateway) を通過した安全なリクエストに対してのみ、
    そのテナント専用のカスタムJWTを持ったSupabaseクライアントを生成して返す。
    """
    if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials are not configured in the environment.",
        )

    # 1. ゼロトラスト: テナントIDを埋め込んだカスタムJWTペイロードを作成
    payload = {
        "role": "authenticated",  # SupabaseのRLSを有効化するための必須ロール
        "tenant_id": tenant_id,  # SQLの `auth.jwt() ->> 'tenant_id'` で参照される値
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # トークンの有効期限 (1時間)
    }

    # 2. PyJWT を使って署名 (HS256)
    try:
        custom_jwt = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: Failed to sign tenant token. {str(e)}",
        )

    # 3. 署名済みJWTをAuthorizationヘッダーにセットした専用クライアントを生成
    # ※リクエストごとに独立したインスタンスを作成し、コンタミネーションを防ぐ
    options = ClientOptions(headers={"Authorization": f"Bearer {custom_jwt}"})
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

    return client
