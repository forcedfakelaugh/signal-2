import asyncio
import json
import numpy as np

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Cluster, ClusterItem, Insight
from ai_posts.llm.client import smart_generate_json_async, embed_single
from ai_posts.llm.prompts import distill_cluster
from ai_posts.config import settings


async def process_cluster(cluster, semaphore, session):
    """Distill insights for a single cluster."""
    async with semaphore:
        # Gather comment texts for this cluster
        comments = [item.comment.text for item in cluster.items]

        # Cap at 50 comments to stay within context window
        if len(comments) > 50:
            comments = comments[:50]

        # Ask LLM to distill
        system, user = distill_cluster(comments)
        try:
            raw = await smart_generate_json_async(user, system=system)
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return []

        new_insights = []
        for item in result.get("insights", [])[:settings.insights_per_cluster]:
            text = item.get("text", "").strip()
            if not text:
                continue

            # Embed the insight for later dedup / novelty (this is sync for now as it uses batching internally but we call embed_single)
            # Actually embed_single is sync in client.py. Let's leave it for now or make it async if needed.
            embedding = embed_single(text)

            # Check dedup against existing insights (similarity > 0.85)
            # Fetch fresh list for each check to avoid parallel dupes as much as possible
            # Note: This is still slightly race-prone but much better than nothing.
            existing = session.execute(select(Insight)).scalars().all()
            is_duplicate = False
            if existing:
                for ex in existing:
                    if ex.embedding is not None:
                        sim = np.dot(embedding, ex.embedding) / (
                            np.linalg.norm(embedding) * np.linalg.norm(ex.embedding)
                        )
                        if sim > settings.novelty_threshold:
                            is_duplicate = True
                            break

            if is_duplicate:
                continue

            insight = Insight(
                cluster_id=cluster.id,
                text=text,
                embedding=embedding,
            )
            new_insights.append(insight)
            # Add to session immediately so next checks see it (though technically they need to commit)
            # SQLAlchemy session isn't thread-safe, but asyncio is single-threaded.
            # However, session.execute is blocking.
            session.add(insight)

        return new_insights


async def _run_async() -> int:
    """Async implementation of insight distillation."""
    session = get_session()
    try:
        # Get top clusters by score
        stmt = (
            select(Cluster)
            .options(joinedload(Cluster.items).joinedload(ClusterItem.comment))
            .order_by(Cluster.score.desc())
            .limit(settings.top_clusters)
        )
        clusters = session.execute(stmt).unique().scalars().all()

        if not clusters:
            raise ValueError("No clusters found. Run `cluster` first.")

        semaphore = asyncio.Semaphore(5)  # Distillation is heavier, lower concurrency
        tasks = [process_cluster(c, semaphore, session) for c in clusters]
        results = await asyncio.gather(*tasks)

        # Flatten and count (session.add was called in process_cluster)
        all_created = [i for sublist in results for i in sublist]
        session.commit()

        return len(all_created)
    finally:
        session.close()


def run() -> int:
    """Wrapper to run the async pipeline stage from the sync CLI."""
    return asyncio.run(_run_async())

