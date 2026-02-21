"""
Stage 3: Distill top clusters into human insights using LLM.
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ai_posts.db.engine import get_session
from ai_posts.db.models import Cluster, ClusterItem, Insight
from ai_posts.llm.client import smart_generate_json, embed_single
from ai_posts.llm.prompts import distill_cluster
from ai_posts.config import settings


def run() -> int:
    """Distill top clusters into insights. Returns number of insights created."""
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

        insight_count = 0
        for cluster in clusters:
            # Gather comment texts for this cluster
            comments = [item.comment.text for item in cluster.items]

            # Cap at 50 comments to stay within context window
            if len(comments) > 50:
                comments = comments[:50]

            # Ask LLM to distill
            system, user = distill_cluster(comments)
            raw = smart_generate_json(user, system=system)

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                continue

            for item in result.get("insights", [])[:settings.insights_per_cluster]:
                text = item.get("text", "").strip()
                if not text:
                    continue

                # Embed the insight for later dedup / novelty
                embedding = embed_single(text)

                # Check dedup against existing insights (similarity > 0.85)
                existing = session.execute(select(Insight)).scalars().all()
                is_duplicate = False
                if existing:
                    import numpy as np
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
                session.add(insight)
                insight_count += 1

        session.commit()
        return insight_count
    finally:
        session.close()
