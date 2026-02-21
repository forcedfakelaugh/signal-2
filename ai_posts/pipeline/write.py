"""
Stage 6: Write full posts from top hooks, with persona rewrite and novelty check.
"""

import json

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Hook, Post, Angle, Insight
from ai_posts.llm.client import generate_json, embed_single
from ai_posts.llm.prompts import write_post, persona_rewrite
from ai_posts.config import settings


def _check_novelty(embedding: list[float], session) -> bool:
    """Check if a post is novel enough compared to past posts.

    Returns True if novel (should keep), False if too similar (should reject).
    """
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


def run() -> int:
    """Write posts from top unprocessed hooks. Returns count of posts created."""
    session = get_session()
    try:
        # Find hooks that don't have posts yet, ordered by score
        hooks_stmt = (
            select(Hook)
            .options(
                joinedload(Hook.angle).joinedload(Angle.insight).joinedload(Insight.cluster)
            )
            .where(~Hook.posts.any())
            .where(Hook.weighted_score.isnot(None))
            .order_by(Hook.weighted_score.desc())
            .limit(settings.top_posts_output * 2)  # generate extra, novelty will filter
        )
        hooks = session.execute(hooks_stmt).unique().scalars().all()

        if not hooks:
            return 0

        post_count = 0
        for hook in hooks:
            if post_count >= settings.top_posts_output:
                break

            # Load related data
            angle = hook.angle
            insight = angle.insight if angle else None

            insight_text = insight.text if insight else ""
            angle_text = angle.text if angle else ""

            # Write the post
            system, user = write_post(hook.text, insight_text, angle_text)
            raw = generate_json(user, system=system)

            try:
                result = json.loads(raw)
                content = result.get("content", "").strip()
            except (json.JSONDecodeError, AttributeError):
                continue

            if not content:
                continue

            # Persona rewrite
            p_system, p_user = persona_rewrite(content)
            p_raw = generate_json(p_user, system=p_system)

            try:
                p_result = json.loads(p_raw)
                rewritten = p_result.get("content", content).strip()
            except (json.JSONDecodeError, AttributeError):
                rewritten = content

            # Embed for novelty check
            embedding = embed_single(rewritten)

            # Novelty check
            if not _check_novelty(embedding, session):
                continue

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
            session.flush()
            post_count += 1

        session.commit()
        return post_count
    finally:
        session.close()
