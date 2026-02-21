"""
YouTube comment collection via the YouTube Data API v3.

Usage:
    from ai_posts.sources.youtube import collect_video_comments
    comments = collect_video_comments("dQw4w9WgXcQ", max_comments=500)
"""

import re

import httpx

from ai_posts.config import settings


def collect_video_comments(
    video_id: str,
    *,
    max_comments: int = 1000,
) -> list[dict]:
    """Fetch top-level comments from a YouTube video.

    Returns list of dicts with keys: source_id, text, author, metadata.
    """
    if not settings.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is required for YouTube collection")

    comments: list[dict] = []
    page_token: str | None = None
    url = "https://www.googleapis.com/youtube/v3/commentThreads"

    while len(comments) < max_comments:
        params: dict = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": min(100, max_comments - len(comments)),
            "order": "relevance",
            "textFormat": "plainText",
            "key": settings.youtube_api_key,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet["textDisplay"].strip()

            # Apply quality filters
            if not _passes_filter(text):
                continue

            comments.append({
                "source": "youtube",
                "source_id": item["snippet"]["topLevelComment"]["id"],
                "text": text,
                "author": snippet.get("authorDisplayName"),
                "metadata": {
                    "video_id": video_id,
                    "like_count": snippet.get("likeCount", 0),
                    "published_at": snippet.get("publishedAt"),
                },
            })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return comments


def collect_channel_comments(
    channel_id: str,
    *,
    max_videos: int = 10,
    max_comments_per_video: int = 200,
) -> list[dict]:
    """Collect comments from recent videos of a channel."""
    video_ids = _get_channel_videos(channel_id, max_results=max_videos)
    all_comments: list[dict] = []

    for vid in video_ids:
        comments = collect_video_comments(vid, max_comments=max_comments_per_video)
        all_comments.extend(comments)

    return all_comments


def _get_channel_videos(channel_id: str, max_results: int = 10) -> list[str]:
    """Get recent video IDs from a channel."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "id",
        "channelId": channel_id,
        "maxResults": max_results,
        "order": "date",
        "type": "video",
        "key": settings.youtube_api_key,
    }
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    return [item["id"]["videoId"] for item in data.get("items", [])]


# ── Filters ───────────────────────────────────────────────────────────────

_URL_PATTERN = re.compile(r"https?://\S+")


def _passes_filter(text: str) -> bool:
    """Filter out low-quality comments. Keep personal, substantive ones."""
    # Too short
    if len(text.split()) < 8:
        return False

    # Spam: mostly URLs
    if _URL_PATTERN.search(text) and len(text) < 100:
        return False

    # Contains personal signal words (loose check)
    # We want comments with "I", "my", "we" — personal experiences
    lower = text.lower()
    has_personal = any(w in lower.split() for w in ("i", "my", "me", "we", "our", "i've", "i'm"))

    # Longer comments are valuable even without personal pronouns
    if len(text.split()) > 30:
        return True

    return has_personal
