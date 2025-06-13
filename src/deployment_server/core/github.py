import hashlib
import hmac
from deployment_server.config import config


def verify_signature(body, signature):
    secret_token = config.github_webhook_secret_token

    if not secret_token:
        raise ValueError("Missing github_webhook_secret_token.")

    # Create HMAC with SHA256
    calculated_signature = (
        "sha256="
        + hmac.new(
            secret_token.encode("utf-8"),
            body.encode("utf-8") if isinstance(body, str) else body,
            hashlib.sha256,
        ).hexdigest()
    )

    # Use hmac.compare_digest for timing-safe comparison
    return hmac.compare_digest(signature, calculated_signature)
