"""
Application configuration via environment variables.

All settings load from .env file or environment.
Scoring weights are hardcoded defaults for MVP — will move to DB after signal validation.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────
    database_url: str

    # ── LLM ───────────────────────────────────────────────────────────
    openai_api_key: str
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model_fast: str = "gpt-4o-mini"
    llm_model_smart: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── Sources ───────────────────────────────────────────────────────
    youtube_api_key: str = ""
    youtube_channel_ids: str = ""

    # ── Hook Scoring Weights (MVP: hardcoded, later: DB/JSON) ────────
    weight_curiosity: float = 1.0
    weight_clarity: float = 1.0
    weight_specificity: float = 1.2  # slightly favor specific hooks
    weight_emotional: float = 1.0
    weight_contrarian: float = 0.8
    weight_shareability: float = 1.0

    # ── Cluster Scoring ───────────────────────────────────────────────
    weight_cluster_size: float = 0.6
    weight_cross_source: float = 0.4

    # ── Novelty ───────────────────────────────────────────────────────
    novelty_threshold: float = 0.85  # reject posts with cosine sim > this

    # ── Content Niche & Audience ──────────────────────────────────────
    # Short label for this niche (used in logs and workflow naming)
    niche_label: str = "tech-careers"

    # The topic/domain the pipeline focuses on (used to filter insights)
    content_niche: str = (
        "software developers, tech workers, or people navigating "
        "AI's impact on technical careers"
    )

    # The specific persona the generated content speaks to / is written for
    target_audience: str = (
        "software engineers and tech workers who are navigating "
        "AI's impact on their careers and daily work"
    )

    # ── Pipeline Defaults ─────────────────────────────────────────────
    top_clusters: int = 15
    insights_per_cluster: int = 3
    angles_per_insight: int = 4
    hooks_per_angle: int = 7
    top_hooks_per_insight: int = 3
    top_posts_output: int = 5

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def youtube_channel_ids_list(self) -> list[str]:
        """Parse comma-separated channel IDs from YOUTUBE_CHANNEL_IDS."""
        if not self.youtube_channel_ids.strip():
            return []
        return [item.strip() for item in self.youtube_channel_ids.split(",") if item.strip()]


# Singleton — import this everywhere
settings = Settings()
