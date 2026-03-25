import os
import time

import jwt  # 🚨 FIX: Migrated from vulnerable python-jose to PyJWT
from fastapi import Depends, HTTPException, status
from supabase import Client, ClientOptions, create_client

# Import the Zero Trust gateway verification
from app.utils.guardian import verify_gateway

# Load secrets from environment variables at startup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")


def get_tenant_db_client(tenant_id: str = Depends(verify_gateway)) -> Client:
    """
    FastAPI Dependency:
    Generates and returns a Supabase client with a custom JWT dedicated to the tenant,
    ONLY for secure requests that have passed the Zero Trust gateway (verify_gateway).
    """
    if not SUPABASE_URL or not SUPABASE_KEY or not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials are not configured in the environment.",
        )

    # 1. Zero Trust: Create a custom JWT payload embedding the tenant ID
    payload = {
        "role": "authenticated",  # Required role to enable Supabase RLS
        "tenant_id": tenant_id,  # Value referenced by `auth.jwt() ->> 'tenant_id'` in SQL
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # Token expiration time (1 hour)
    }

    # 2. Sign using PyJWT (HS256)
    try:
        custom_jwt = jwt.encode(payload, SUPABASE_JWT_SECRET, algorithm="HS256")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: Failed to sign tenant token. {str(e)}",
        )

    # 3. Generate a dedicated client with the signed JWT set in the Authorization header
    # * Create an independent instance per request to prevent cross-tenant data contamination
    options = ClientOptions(headers={"Authorization": f"Bearer {custom_jwt}"})
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

    return client
