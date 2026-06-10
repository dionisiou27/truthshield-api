"""
Lightweight LLM health & error-classification helpers.

No heavy dependencies (works on duck-typed exception attributes), so it can be
imported by both the engine and the API startup path, and unit-tested without
the full app or the openai SDK.
"""
from typing import Callable, Optional, Set
import logging

logger = logging.getLogger(__name__)


def classify_llm_error(exc: Exception) -> str:
    """Map an LLM/provider exception to a generic, safe degradation category.

    Never returns provider error text — only a stable category string:
      - "llm_misconfigured"  → model not found / 404 (e.g. a deprecated model id)
      - "llm_auth"           → 401/403 auth or permission error
      - "llm_quota"          → 429 rate limit / quota exhausted
      - "llm_timeout"        → request timeout
      - "llm_error"          → anything else
    """
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    msg = str(exc).lower()

    code = None
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            code = err.get("code")

    if (
        code == "model_not_found"
        or "model_not_found" in msg
        or "does not exist" in msg
        or "notfound" in name
        or status == 404
    ):
        return "llm_misconfigured"
    if (
        status in (401, 403)
        or "authentication" in name
        or "permissiondenied" in name
        or "invalid_api_key" in msg
    ):
        return "llm_auth"
    if status == 429 or "ratelimit" in name or "quota" in msg:
        return "llm_quota"
    if "timeout" in name or "timeout" in msg:
        return "llm_timeout"
    return "llm_error"


def validate_llm_model(
    model: str,
    api_key: Optional[str],
    timeout: float = 5.0,
    fetcher: Optional[Callable[[], Set[str]]] = None,
) -> str:
    """Check whether ``model`` is available on the account.

    Returns:
      - "ok"            → model present in the account's model list
      - "misconfigured" → model NOT present (logs CRITICAL)
      - "unknown"       → could not determine (no key, network error, non-200)

    ``fetcher`` lets callers/tests inject the available model-id set without a
    network call. Never raises — a failed lookup degrades to "unknown".
    """
    if not api_key:
        return "unknown"
    try:
        if fetcher is not None:
            ids = set(fetcher())
        else:
            import httpx

            resp = httpx.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=timeout,
            )
            if resp.status_code != 200:
                return "unknown"
            ids = {m.get("id") for m in resp.json().get("data", [])}

        if model in ids:
            return "ok"
        logger.critical(
            "Configured LLM model '%s' is NOT available on this account. "
            "LLM features will run in degraded mode until OPENAI_MODEL_GENERATION "
            "is set to a valid model id.",
            model,
        )
        return "misconfigured"
    except Exception as exc:  # pragma: no cover - defensive; never block startup
        logger.warning("LLM model validation skipped (%s)", type(exc).__name__)
        return "unknown"
