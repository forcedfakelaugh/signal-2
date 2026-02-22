import asyncio
import json

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Hook, Post, Angle, Insight
from ai_posts.llm.client import smart_generate_json_async, embed_single
from ai_posts.llm.prompts import write_post, persona_rewrite
from ai_posts.config import settings


def _check_novelty(embedding: list[float], session) -> bool:
    """Check if a post is novel enough compared to past posts."""
    stmt = select(Post).where(Post.embedding.isnot(None))
    existing = session.execute(stmt).scalars().all()

    if not existing:
        return True

    emb = np.array(embedding)
    for post in existing:
        past_emb = np.array(post.embedding)
        sim = np.dot(emb, past_emb) / (
            np.linalg.norm(emb) * np.linalg.norm(past_emb) + 1e-8
        )
        if sim > settings.novelty_threshold:
            return False

    return True


async def process_hook(hook, semaphore, session):
    """Write a post for a single hook."""
    async with semaphore:
        # Load related data
        angle = hook.angle
        insight = angle.insight if angle else None

        insight_text = insight.text if insight else ""
        angle_text = angle.text if angle else ""

        # Write the post
        system, user = write_post(hook.text, insight_text, angle_text)
        try:
            raw = await smart_generate_json_async(user, system=system)
            result = json.loads(raw)
            content = result.get("content", "").strip()
        except (json.JSONDecodeError, AttributeError, Exception):
            return None

        if not content:
            return None

        # Persona rewrite
        p_system, p_user = persona_rewrite(content)
        try:
            p_raw = await smart_generate_json_async(p_user, system=p_system)
            p_result = json.loads(p_raw)
            rewritten = p_result.get("content", content).strip()
        except (json.JSONDecodeError, AttributeError, Exception):
            rewritten = content

        # Embed for novelty check
        embedding = embed_single(rewritten)

        # Novelty check (synchronized check)
        if not _check_novelty(embedding, session):
            return None

        # Calculate predicted score (hook score + cluster weight)
        cluster_weight = 0.0
        if insight and insight.cluster:
            cluster_weight = insight.cluster.score

        predicted_score = (hook.weighted_score or 0) + cluster_weight

        # Save post
        post = Post(
            hook_id=hook.id,
            content=rewritten,
            embedding=embedding,
            predicted_score=predicted_score,
        )
        session.add(post)
        return post


async def _run_async() -> int:
    """Async implementation of post writing."""
    session = get_session()
    try:
        # Find hooks that don't have posts yet
        hooks_stmt = (
            select(Hook)
            .options(
                joinedload(Hook.angle).joinedload(Angle.insight).joinedload(Insight.cluster)
            )
            .where(~Hook.posts.any())
            .where(Hook.weighted_score.isnot(None))
            .order_by(Hook.weighted_score.desc())
            .limit(settings.top_posts_output * 2)
        )
        hooks = session.execute(hooks_stmt).unique().scalars().all()

        if not hooks:
            return 0

        semaphore = asyncio.Semaphore(5)
        tasks = [process_hook(hook, semaphore, session) for hook in hooks]

        # Process one by one if we need strict ranking/limit, 
        # but gather is faster. We'll gather and then limit at the end.
        results = await asyncio.gather(*tasks)

        # Filter out Nones and limit to required count
        created_posts = [p for p in results if p is not None]
        created_posts = created_posts[:settings.top_posts_output]

        # Only those in created_posts should be committed (they were added to session in process_hook)
        session.commit()
        return len(created_posts)
    finally:
        session.close()


def run() -> int:
    """Wrapper to run the async pipeline stage from the sync CLI."""
    return asyncio.run(_run_async())

