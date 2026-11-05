"""Embedders for a vector store: the Voyage AI and OpenAI embedder factories and the embedder id strings that name a
model family (stored on card points).

Every setting is an argument: the model names and keys are passed in, and no environment variable is read here. The
``voyageai`` and ``openai`` libraries are per-arm extras (``voyage``, ``openai``) imported only when a factory is called.
The memory bound on a batch is the store's (``QdrantVectorStore``); the defaults it measured live here.
"""
from __future__ import annotations

from typing import Callable, List, Optional

DEFAULT_VOYAGE_MODEL = "voyage-3-lite"
DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


def make_voyage_embedder(
    *,
    model: str = DEFAULT_VOYAGE_MODEL,
    input_type: str = "document",
    api_key: Optional[str] = None,
) -> Callable[[List[str]], List[List[float]]]:
    """Build a Voyage AI-backed embedding callable.

    ``input_type`` is ``"document"`` for items being stored and ``"query"`` for search queries: pass a separate
    embedder per role so an asymmetric embedding is reproduced correctly. ``api_key`` is the Voyage key; when omitted
    the ``voyageai`` library's own default lookup is used. Errors propagate to the caller (the store swallows them).
    Raises ``ImportError`` at factory-call time when ``voyageai`` is not installed.
    """
    try:
        import voyageai  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "make_voyage_embedder requires the voyageai package. "
            "Install with: pip install voyageai"
        ) from exc

    _model = model
    _input_type = input_type
    _api_key = api_key

    def _embed(texts: List[str]) -> List[List[float]]:
        import voyageai as _va
        client = _va.Client(api_key=_api_key)
        return client.embed(texts, model=_model, input_type=_input_type).embeddings

    return _embed


def make_openai_embedder(
    *,
    model: str = DEFAULT_OPENAI_EMBEDDING_MODEL,
    api_key: Optional[str] = None,
) -> Callable[[List[str]], List[List[float]]]:
    """Build an OpenAI-backed embedding callable.

    OpenAI embeddings are symmetric (no ``input_type`` distinction), so the same callable can be passed as both
    ``embedder`` and ``query_embedder``. ``api_key`` is the OpenAI key; when omitted the ``openai`` library's own
    default lookup is used. Raises ``ImportError`` at factory-call time when ``openai`` is not installed.
    """
    try:
        import openai  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "make_openai_embedder requires the openai package. "
            "Install with: pip install openai"
        ) from exc

    _model = model
    _api_key = api_key

    def _embed(texts: List[str]) -> List[List[float]]:
        import openai as _oa
        client = _oa.OpenAI(api_key=_api_key)
        response = client.embeddings.create(input=texts, model=_model)
        return [item.embedding for item in response.data]

    return _embed


# How many texts may be in the embedder at once. This is a MEMORY bound, not a throughput one.
#
# A transformer embedder's attention tensor is ``batch x heads x seq^2 x 4`` bytes, so at the
# default model's 512-token window each text in flight costs on the order of 12MB -- and the ONNX
# arena that serves those allocations grows to the high-water mark and does not give it back.
# MEASURED over 5,678 card-sized texts (peak RSS of the whole process):
#     whole corpus in one call   5571MB in production, and an allocation failure under a 3GB cap
#     batch 128                  a single 1.5GiB attention allocation -> failure
#     batch 32                   a single 384MB attention allocation -> failure
#     batch 16                   completed cleanly, 797MB
# 16 is therefore the default: the first size whose largest single allocation fits comfortably,
# chosen from measurement rather than from what looks like a reasonable round number. Raising it
# trades memory headroom for fewer round trips; a deployment with more RAM says so with the store's
# ``embed_batch_size`` argument.
EMBED_BATCH_DEFAULT = 16
# Per-text cap for EMBEDDING only (payloads keep the full text). The default model truncates at
# its context window regardless, so anything beyond this costs tokenizer memory for tokens that
# are then discarded.
EMBED_MAX_CHARS_DEFAULT = 8000


FASTEMBED_MODEL_NAME = "BAAI/bge-small-en-v1.5"
FASTEMBED_EMBEDDER_ID = f"fastembed:{FASTEMBED_MODEL_NAME}"


def voyage_embedder_id(model: str = DEFAULT_VOYAGE_MODEL) -> str:
    return f"voyage:{model}"


def openai_embedder_id(model: str = DEFAULT_OPENAI_EMBEDDING_MODEL) -> str:
    return f"openai:{model}"


def embedder_id_for(backend: str = "", *, voyage_model: str = DEFAULT_VOYAGE_MODEL,
                    openai_model: str = DEFAULT_OPENAI_EMBEDDING_MODEL) -> str:
    """The embedder family a backend name (``voyage``, ``openai``, anything else for the local default) selects, as an id."""
    backend = (backend or "").strip().lower()
    if backend == "voyage":
        return voyage_embedder_id(voyage_model)
    if backend == "openai":
        return openai_embedder_id(openai_model)
    return FASTEMBED_EMBEDDER_ID
