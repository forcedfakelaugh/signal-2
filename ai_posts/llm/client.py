"""
Provider-agnostic LLM client.

Uses the OpenAI SDK which works with OpenAI, OpenRouter, Groq, Together,
and any OpenAI-compatible API via LLM_BASE_URL.
"""

from openai import OpenAI

from ai_posts.config import settings

# Single client instance — reused across all pipeline stages
_client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.llm_base_url,
)


def generate(
    prompt: str,
    *,
    system: str = "You are a helpful assistant.",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    response_format: dict | None = None,
) -> str:
    """Generate text completion. Uses fast model by default."""
    kwargs: dict = {
        "model": model or settings.llm_model_fast,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    response = _client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""


def generate_json(
    prompt: str,
    *,
    system: str = "You are a helpful assistant. Respond in valid JSON only.",
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> str:
    """Generate structured JSON output. Lower temperature for consistency."""
    return generate(
        prompt,
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )


def smart_generate(
    prompt: str,
    *,
    system: str = "You are a helpful assistant.",
    temperature: float = 0.5,
    max_tokens: int = 4096,
    response_format: dict | None = None,
) -> str:
    """Generate using the smart (expensive) model. Use for scoring/critique."""
    return generate(
        prompt,
        system=system,
        model=settings.llm_model_smart,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
    )


def smart_generate_json(
    prompt: str,
    *,
    system: str = "You are a helpful assistant. Respond in valid JSON only.",
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> str:
    """Generate structured JSON using the smart model."""
    return generate_json(
        prompt,
        system=system,
        model=settings.llm_model_smart,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def embed(texts: list[str], *, batch_size: int = 100) -> list[list[float]]:
    """Generate embeddings for a list of texts. Handles batching.

    Returns list of embedding vectors (each is list[float] of EMBEDDING_DIM).
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = _client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def embed_single(text: str) -> list[float]:
    """Embed a single text string."""
    return embed([text])[0]
