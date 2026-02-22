import asyncio
import json

from sqlalchemy import select

from ai_posts.db.engine import get_session
from ai_posts.db.models import Insight, Angle
from ai_posts.llm.client import generate_json_async
from ai_posts.llm.prompts import generate_angles
from ai_posts.config import settings


async def process_insight(insight, semaphore):
    """Generate angles for a single insight."""
    async with semaphore:
        system, user = generate_angles(insight.text)
        try:
            raw = await generate_json_async(user, system=system)
            result = json.loads(raw)
        except (json.JSONDecodeError, Exception):
            return []

        created_angles = []
        for item in result.get("angles", [])[:settings.angles_per_insight]:
            frame = item.get("frame_type", "unknown")
            text = item.get("text", "").strip()
            if not text:
                continue

            created_angles.append(Angle(
                insight_id=insight.id,
                frame_type=frame,
                text=text,
            ))
        return created_angles


async def _run_async() -> int:
    """Async implementation of angle generation."""
    session = get_session()
    try:
        # Find insights without angles
        stmt = select(Insight).where(~Insight.angles.any())
        insights = session.execute(stmt).scalars().all()

        if not insights:
            return 0

        semaphore = asyncio.Semaphore(10)
        tasks = [process_insight(insight, semaphore) for insight in insights]
        results = await asyncio.gather(*tasks)

        new_angles = [angle for sublist in results for angle in sublist]

        if new_angles:
            session.add_all(new_angles)
            session.commit()

        return len(new_angles)
    finally:
        session.close()


def run() -> int:
    """Wrapper to run the async pipeline stage from the sync CLI."""
    return asyncio.run(_run_async())

