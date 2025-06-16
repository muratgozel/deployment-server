import hashlib
import hmac
from typing import Annotated
from dependency_injector import providers
from dependency_injector.wiring import inject, Provide
from deployment_server.containers import ServerContainer


@inject
def verify_signature(
    body,
    signature,
    token: Annotated[
        providers.ConfigurationOption,
        Provide[ServerContainer.gateways.config.github_webhook_secret_token],
    ],
):
    secret_token = token()

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
