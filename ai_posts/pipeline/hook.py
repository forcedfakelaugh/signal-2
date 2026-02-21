"""
Stage 5: Generate hooks and score them with a structured rubric.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Angle, Hook
from ai_posts.llm.client import generate_json, smart_generate
from ai_posts.llm.prompts import generate_hooks, score_hooks
from ai_posts.config import settings


def _weighted_score(scores: dict) -> float:
    """Calculate weighted score from rubric dimensions."""
    return (
        settings.weight_curiosity * scores.get("curiosity", 0)
        + settings.weight_clarity * scores.get("clarity", 0)
        + settings.weight_specificity * scores.get("specificity", 0)
        + settings.weight_emotional * scores.get("emotional_weight", 0)
        + settings.weight_contrarian * scores.get("contrarian", 0)
        + settings.weight_shareability * scores.get("shareability", 0)
    )


def run() -> int:
    """Generate and score hooks for angles without hooks. Returns count."""
    session = get_session()
    try:
        # Find angles without hooks
        stmt = (
            select(Angle)
            .options(joinedload(Angle.insight))
            .where(~Angle.hooks.any())
        )
        angles = session.execute(stmt).unique().scalars().all()

        if not angles:
            return 0

        hook_count = 0
        for angle in angles:
            insight_text = angle.insight.text if angle.insight else ""

            # Generate hooks
            system, user = generate_hooks(angle.text, insight_text)
            raw = generate_json(user, system=system)

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                continue

            hook_texts = [h["text"] for h in result.get("hooks", []) if h.get("text")]
            if not hook_texts:
                continue

            # Score hooks using smart model
            score_sys, score_user = score_hooks(hook_texts)
            score_raw = smart_generate(
                score_user,
                system=score_sys,
                response_format={"type": "json_object"},
            )

            try:
                score_result = json.loads(score_raw)
            except json.JSONDecodeError:
                # If scoring fails, save hooks without scores
                for text in hook_texts[:settings.hooks_per_angle]:
                    session.add(Hook(angle_id=angle.id, text=text))
                    hook_count += 1
                continue

            # Match scores to hooks and save
            scores_list = score_result.get("scores", [])
            scored_hooks: list[tuple[str, float, dict]] = []

            for score_item in scores_list:
                idx = score_item.get("hook_index", 0) - 1  # 1-indexed
                if 0 <= idx < len(hook_texts):
                    ws = _weighted_score(score_item)
                    scored_hooks.append((hook_texts[idx], ws, score_item))

            # Sort by weighted score descending, keep top N
            scored_hooks.sort(key=lambda x: x[1], reverse=True)

            for text, ws, scores in scored_hooks[:settings.top_hooks_per_insight]:
                hook = Hook(
                    angle_id=angle.id,
                    text=text,
                    score_curiosity=scores.get("curiosity"),
                    score_clarity=scores.get("clarity"),
                    score_specificity=scores.get("specificity"),
                    score_emotional=scores.get("emotional_weight"),
                    score_contrarian=scores.get("contrarian"),
                    score_shareability=scores.get("shareability"),
                    weighted_score=ws,
                )
                session.add(hook)
                hook_count += 1

            # Commit per angle to avoid parameter limits
            session.commit()

        return hook_count
    finally:
        session.close()
