"""
YouTube comment collection via the YouTube Data API v3.

Usage:
    from ai_posts.sources.youtube import collect_video_comments
    comments = collect_video_comments("dQw4w9WgXcQ", max_comments=500)
"""

import re
from datetime import datetime, timedelta, timezone

import httpx

from ai_posts.config import settings


def search_videos(
    query: str,
    *,
    max_results: int = 20,
    days: int = 7,
    region_code: str | None = None,
    relevance_language: str | None = None,
) -> list[dict]:
    """Search recent high-view YouTube videos for a query."""
    if not settings.youtube_api_key:
        raise ValueError("YOUTUBE_API_KEY is required for YouTube collection")

    search_url = "https://www.googleapis.com/youtube/v3/search"
    collected: list[dict] = []
    page_token: str | None = None
    capped_max = max(1, min(max_results, 200))
    published_after = _iso_utc_days_ago(days)

    while len(collected) < capped_max:
        params: dict[str, str | int] = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "viewCount",
            "maxResults": min(50, capped_max - len(collected)),
            "publishedAfter": published_after,
            "key": settings.youtube_api_key,
        }
        if page_token:
            params["pageToken"] = page_token
        if region_code:
            params["regionCode"] = region_code
        if relevance_language:
            params["relevanceLanguage"] = relevance_language

        resp = httpx.get(search_url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id:
                continue
            collected.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
            })
            if len(collected) >= capped_max:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    details = _get_video_details([v["video_id"] for v in collected])
    enriched: list[dict] = []
    for video in collected:
        stats = details.get(video["video_id"], {})
        enriched.append({
            **video,
            "view_count": int(stats.get("view_count", 0) or 0),
            "like_count": int(stats.get("like_count", 0) or 0),
            "comment_count": int(stats.get("comment_count", 0) or 0),
        })

    enriched.sort(key=lambda x: x["view_count"], reverse=True)
    return enriched


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


def _get_video_details(video_ids: list[str]) -> dict[str, dict]:
    """Fetch per-video statistics from videos.list."""
    if not video_ids:
        return {}

    url = "https://www.googleapis.com/youtube/v3/videos"
    details: dict[str, dict] = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        params = {
            "part": "statistics",
            "id": ",".join(chunk),
            "maxResults": 50,
            "key": settings.youtube_api_key,
        }
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            stats = item.get("statistics", {})
            details[item.get("id", "")] = {
                "view_count": stats.get("viewCount", 0),
                "like_count": stats.get("likeCount", 0),
                "comment_count": stats.get("commentCount", 0),
            }

    return details


def _iso_utc_days_ago(days: int) -> str:
    """Return RFC3339 timestamp for N days ago in UTC."""
    safe_days = max(0, days)
    ts = datetime.now(timezone.utc) - timedelta(days=safe_days)
    return ts.replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
