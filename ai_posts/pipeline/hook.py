"""
Stage 5: Generate hooks and score them with a structured rubric.
"""

import asyncio
import json

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Angle, Hook
from ai_posts.llm.client import generate_json_async, smart_generate_async
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


async def process_angle(angle, semaphore):
    """Process a single angle: generate hooks then score them."""
    async with semaphore:
        insight_text = angle.insight.text if angle.insight else ""

        # Generate hooks
        system, user = generate_hooks(angle.text, insight_text)
        try:
            raw = await generate_json_async(user, system=system)
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return []

        hook_texts = [h["text"] for h in result.get("hooks", []) if h.get("text")]
        if not hook_texts:
            return []

        # Score hooks using smart model
        score_sys, score_user = score_hooks(hook_texts)
        try:
            score_raw = await smart_generate_async(
                score_user,
                system=score_sys,
                response_format={"type": "json_object"},
            )
            score_result = json.loads(score_raw)
        except (json.JSONDecodeError, Exception):
            # If scoring fails, return hooks without scores
            return [Hook(angle_id=angle.id, text=text) for text in hook_texts[:settings.hooks_per_angle]]

        # Match scores to hooks
        scores_list = score_result.get("scores", [])
        scored_hooks_to_create: list[Hook] = []
        temp_scored = []

        for score_item in scores_list:
            idx = score_item.get("hook_index", 0) - 1  # 1-indexed
            if 0 <= idx < len(hook_texts):
                ws = _weighted_score(score_item)
                temp_scored.append((hook_texts[idx], ws, score_item))

        # Sort by weighted score descending, keep top N
        temp_scored.sort(key=lambda x: x[1], reverse=True)

        for text, ws, scores in temp_scored[:settings.top_hooks_per_insight]:
            scored_hooks_to_create.append(Hook(
                angle_id=angle.id,
                text=text,
                score_curiosity=scores.get("curiosity"),
                score_clarity=scores.get("clarity"),
                score_specificity=scores.get("specificity"),
                score_emotional=scores.get("emotional_weight"),
                score_contrarian=scores.get("contrarian"),
                score_shareability=scores.get("shareability"),
                weighted_score=ws,
            ))

        return scored_hooks_to_create


async def _run_async() -> int:
    """Async implementation of hook generation."""
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

        # Process angles in parallel with a limit
        semaphore = asyncio.Semaphore(10)  # max 10 parallel LLM call pairs
        tasks = [process_angle(angle, semaphore) for angle in angles]

        # Use gather to run all tasks
        results = await asyncio.gather(*tasks)

        # Flatten results and save to DB
        new_hooks = [hook for sublist in results for hook in sublist]

        if new_hooks:
            session.add_all(new_hooks)
            session.commit()

        return len(new_hooks)
    finally:
        session.close()


def run() -> int:
    """Wrapper to run the async pipeline stage from the sync CLI."""
    return asyncio.run(_run_async())
