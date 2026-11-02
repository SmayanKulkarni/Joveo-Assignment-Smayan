import boto3
import jwt
import psycopg

from talent_scout.kernel.settings import Settings

BUCKET = "assets"  # declared in neon.ts


def pg_connect(s: Settings) -> psycopg.Connection:
    return psycopg.connect(s.database_url)


def bucket(s: Settings):
    """S3 client for the Neon bucket; Neon hands out standard AWS-style credentials."""
    return boto3.client(
        "s3",
        endpoint_url=s.aws_endpoint_url_s3,
        region_name=s.aws_region,
        aws_access_key_id=s.aws_access_key_id,
        aws_secret_access_key=s.aws_secret_access_key,
    )


def verify_token(s: Settings, token: str) -> dict:
    """Check a Neon Auth JWT against the project's JWKS and return its claims."""
    key = jwt.PyJWKClient(s.neon_auth_jwks_url).get_signing_key_from_jwt(token)
    return jwt.decode(token, key.key, algorithms=["EdDSA", "RS256", "ES256"], options={"verify_aud": False})
