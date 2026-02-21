"""
Stage 2: Cluster embedded comments using HDBSCAN.

No K to tune — HDBSCAN finds natural clusters and labels noise as -1.
"""

import numpy as np
import hdbscan
from sqlalchemy import select

from ai_posts.db.engine import get_session
from ai_posts.db.models import RawComment, Cluster, ClusterItem
from ai_posts.config import settings


def run(min_cluster_size: int = 10) -> int:
    """Cluster all embedded comments. Returns number of clusters found."""
    session = get_session()
    try:
        # Load all embedded comments
        stmt = select(RawComment).where(RawComment.embedding.isnot(None))
        comments = session.execute(stmt).scalars().all()

        if len(comments) < min_cluster_size:
            raise ValueError(
                f"Need at least {min_cluster_size} embedded comments, "
                f"got {len(comments)}. Run `embed` first."
            )

        # Build embedding matrix
        embeddings = np.array([c.embedding for c in comments])

        # Run HDBSCAN
        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric="euclidean",
            cluster_selection_method="eom",
        )
        labels = clusterer.fit_predict(embeddings)

        # Clear old clusters
        session.query(ClusterItem).delete()
        session.query(Cluster).delete()
        session.flush()

        # Create new clusters
        unique_labels = set(labels)
        unique_labels.discard(-1)  # -1 = noise

        cluster_count = 0
        for label in sorted(unique_labels):
            # Find comments in this cluster
            indices = [i for i, l in enumerate(labels) if l == label]
            cluster_comments = [comments[i] for i in indices]

            # Calculate cross-source count
            sources = set(c.source for c in cluster_comments)
            cross_source = len(sources)

            # Calculate cluster score
            size = len(cluster_comments)
            max_size = max(
                len([i for i, l in enumerate(labels) if l == lab])
                for lab in unique_labels
            )
            normalized_size = size / max_size if max_size > 0 else 0

            score = (
                settings.weight_cluster_size * normalized_size
                + settings.weight_cross_source * cross_source
            )

            # Pick representative text (closest to centroid)
            cluster_embeddings = embeddings[indices]
            centroid = cluster_embeddings.mean(axis=0)
            distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
            closest_idx = indices[np.argmin(distances)]
            representative = comments[closest_idx].text

            # Save cluster
            cluster = Cluster(
                label=int(label),
                size=size,
                cross_source_count=cross_source,
                score=score,
                representative_text=representative[:500],
            )
            session.add(cluster)
            session.flush()  # get cluster.id

            # Link comments to cluster
            for comment in cluster_comments:
                session.add(ClusterItem(
                    cluster_id=cluster.id,
                    comment_id=comment.id,
                ))

            cluster_count += 1

        session.commit()
        return cluster_count
    finally:
        session.close()
