"""
Stage 4: Generate narrative angles for each insight.
"""

import json

from sqlalchemy import select

from ai_posts.db.engine import get_session
from ai_posts.db.models import Insight, Angle
from ai_posts.llm.client import generate_json
from ai_posts.llm.prompts import generate_angles
from ai_posts.config import settings


def run() -> int:
    """Generate angles for insights that don't have any yet. Returns count."""
    session = get_session()
    try:
        # Find insights without angles
        stmt = select(Insight).where(~Insight.angles.any())
        insights = session.execute(stmt).scalars().all()

        if not insights:
            return 0

        angle_count = 0
        for insight in insights:
            system, user = generate_angles(insight.text)
            raw = generate_json(user, system=system)

            try:
                result = json.loads(raw)
            except json.JSONDecodeError:
                continue

            for item in result.get("angles", [])[:settings.angles_per_insight]:
                frame = item.get("frame_type", "unknown")
                text = item.get("text", "").strip()
                if not text:
                    continue

                angle = Angle(
                    insight_id=insight.id,
                    frame_type=frame,
                    text=text,
                )
                session.add(angle)
                angle_count += 1

        session.commit()
        return angle_count
    finally:
        session.close()
