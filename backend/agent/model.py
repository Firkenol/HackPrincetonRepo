"""Loads the chat model named by environment variables.

MODEL_PROVIDER and MODEL_ID are passed to LangChain's provider-agnostic
init_chat_model, so swapping provider is an environment change, not a code change.
Each provider reads its own credentials from its usual environment variables
(see .env.example at the repo root). No provider is required by the code.
"""

from __future__ import annotations

import os

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

PROVIDER_VAR = "MODEL_PROVIDER"
MODEL_VAR = "MODEL_ID"
MAX_RETRIES = 8


class ModelNotConfigured(RuntimeError):
    """MODEL_PROVIDER or MODEL_ID is not set."""


def is_configured() -> bool:
    return bool(os.environ.get(PROVIDER_VAR, "").strip() and os.environ.get(MODEL_VAR, "").strip())


def load_model() -> BaseChatModel:
    provider = os.environ.get(PROVIDER_VAR, "").strip()
    model_id = os.environ.get(MODEL_VAR, "").strip()
    if not provider or not model_id:
        raise ModelNotConfigured(f"Set {PROVIDER_VAR} and {MODEL_VAR} to choose a model. See .env.example.")
    # temperature 0: extraction should be repeatable.
    # One listing takes about eight model calls, which a low requests-per-minute quota
    # throttles. max_retries makes the provider's client wait and retry with backoff
    # instead of failing the run.
    return init_chat_model(model_id, model_provider=provider, temperature=0, max_retries=MAX_RETRIES)
