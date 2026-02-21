"""
CLI interface for the AI Posts pipeline.

Usage:
    ai-posts collect youtube VIDEO_ID
    ai-posts collect-channels
    ai-posts find-videos "ai agents"
    ai-posts embed
    ai-posts cluster
    ai-posts distill
    ai-posts angles
    ai-posts hooks
    ai-posts write
    ai-posts today         # runs the full pipeline
    ai-posts show          # show top unposted posts
    ai-posts init-db       # create tables + pgvector extension
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(
    name="ai-posts",
    help="Signal-first AI content generation pipeline",
    no_args_is_help=True,
)
console = Console()


# ── Database ──────────────────────────────────────────────────────────────


@app.command()
def init_db():
    """Create database tables and enable pgvector extension."""
    from sqlalchemy import text
    from ai_posts.db.engine import engine
    from ai_posts.db.models import Base

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    Base.metadata.create_all(engine)
    console.print("[green]✓[/green] Database tables created with pgvector extension")


# ── Collection ────────────────────────────────────────────────────────────


@app.command()
def collect(
    source: str = typer.Argument(help="Source type: youtube"),
    target: str = typer.Argument(help="Video ID, Channel ID, etc."),
    max_comments: int = typer.Option(1000, "--max", "-m", help="Max comments to collect"),
):
    """Collect raw comments from a source."""
    from ai_posts.pipeline.collect import collect_youtube_video, collect_youtube_channel

    with console.status(f"[bold blue]Collecting from {source}...[/bold blue]"):
        if source == "youtube":
            # Auto-detect: channel IDs start with UC
            if target.startswith("UC"):
                count = collect_youtube_channel(target, max_videos=10)
            else:
                count = collect_youtube_video(target, max_comments=max_comments)
        else:
            console.print(f"[red]Unknown source: {source}[/red]")
            raise typer.Exit(1)

    console.print(f"[green]✓[/green] Collected {count} new comments from {source}")


@app.command("collect-channels")
def collect_channels(
    max_videos: int = typer.Option(10, "--max-videos", help="Recent videos per channel"),
):
    """Collect comments from channels listed in YOUTUBE_CHANNEL_IDS."""
    from ai_posts.config import settings
    from ai_posts.pipeline.collect import collect_youtube_channel

    channel_ids = settings.youtube_channel_ids_list
    if not channel_ids:
        console.print("[yellow]No channels configured. Set YOUTUBE_CHANNEL_IDS in .env.[/yellow]")
        raise typer.Exit(1)

    console.print(f"[bold blue]Collecting from {len(channel_ids)} configured channel(s)...[/bold blue]")
    total = 0
    for channel_id in channel_ids:
        with console.status(f"[bold blue]Collecting {channel_id}...[/bold blue]"):
            count = collect_youtube_channel(channel_id, max_videos=max_videos)
        total += count
        console.print(f"  [green]✓[/green] {channel_id}: {count} new comments")

    console.print(f"[green]✓[/green] Total new comments: {total}")


@app.command("find-videos")
def find_videos(
    query: str = typer.Argument(help="Search query, e.g. 'ai agents'"),
    max_results: int = typer.Option(20, "--max-results", help="Max videos to return (1-200)"),
    days: int = typer.Option(7, "--days", help="Only videos published in the last N days"),
    region_code: str = typer.Option("", "--region", help="Optional region code (e.g. US)"),
    language: str = typer.Option("", "--lang", help="Optional relevance language (e.g. en)"),
):
    """Find recent high-view videos for a topic query."""
    from ai_posts.sources.youtube import search_videos

    with console.status("[bold blue]Searching YouTube videos...[/bold blue]"):
        videos = search_videos(
            query,
            max_results=max_results,
            days=days,
            region_code=region_code or None,
            relevance_language=language or None,
        )

    if not videos:
        console.print("[yellow]No videos found for that query/window.[/yellow]")
        return

    table = Table(title=f"Top Videos for: {query}", show_header=True, header_style="bold magenta")
    table.add_column("Video ID", style="cyan")
    table.add_column("Views", justify="right", style="green")
    table.add_column("Published", style="yellow")
    table.add_column("Channel", style="white")
    table.add_column("Title", style="white")

    for video in videos:
        table.add_row(
            video["video_id"],
            f'{video["view_count"]:,}',
            video["published_at"][:10],
            video["channel_title"][:28],
            video["title"][:72],
        )

    console.print()
    console.print(table)
    console.print()


# ── Pipeline Stages ───────────────────────────────────────────────────────


@app.command()
def embed():
    """Generate embeddings for all un-embedded comments."""
    from ai_posts.pipeline.embed import run

    with console.status("[bold blue]Generating embeddings...[/bold blue]"):
        count = run()

    console.print(f"[green]✓[/green] Embedded {count} comments")


@app.command()
def cluster(
    min_size: int = typer.Option(10, "--min-size", help="Minimum cluster size"),
):
    """Cluster embedded comments using HDBSCAN."""
    from ai_posts.pipeline.cluster import run

    with console.status("[bold blue]Clustering...[/bold blue]"):
        count = run(min_cluster_size=min_size)

    console.print(f"[green]✓[/green] Found {count} clusters")


@app.command()
def distill():
    """Distill top clusters into human insights."""
    from ai_posts.pipeline.distill import run

    with console.status("[bold blue]Distilling insights...[/bold blue]"):
        count = run()

    console.print(f"[green]✓[/green] Created {count} insights")


@app.command()
def angles():
    """Generate narrative angles for insights."""
    from ai_posts.pipeline.angle import run

    with console.status("[bold blue]Generating angles...[/bold blue]"):
        count = run()

    console.print(f"[green]✓[/green] Generated {count} angles")


@app.command()
def hooks():
    """Generate and score hooks for angles."""
    from ai_posts.pipeline.hook import run

    with console.status("[bold blue]Generating & scoring hooks...[/bold blue]"):
        count = run()

    console.print(f"[green]✓[/green] Created {count} scored hooks")


@app.command()
def write():
    """Write full posts from top hooks."""
    from ai_posts.pipeline.write import run

    with console.status("[bold blue]Writing posts...[/bold blue]"):
        count = run()

    console.print(f"[green]✓[/green] Wrote {count} posts")


# ── Orchestration ─────────────────────────────────────────────────────────


@app.command()
def today():
    """Run the full pipeline: embed → cluster → distill → angles → hooks → write → show."""
    from ai_posts.pipeline import embed as embed_mod
    from ai_posts.pipeline import cluster as cluster_mod
    from ai_posts.pipeline import distill as distill_mod
    from ai_posts.pipeline import angle as angle_mod
    from ai_posts.pipeline import hook as hook_mod
    from ai_posts.pipeline import write as write_mod

    stages = [
        ("Embedding comments", embed_mod.run, {}),
        ("Clustering", cluster_mod.run, {}),
        ("Distilling insights", distill_mod.run, {}),
        ("Generating angles", angle_mod.run, {}),
        ("Generating hooks", hook_mod.run, {}),
        ("Writing posts", write_mod.run, {}),
    ]

    console.print()
    console.rule("[bold blue]AI Posts — Daily Pipeline[/bold blue]")
    console.print()

    for label, func, kwargs in stages:
        with console.status(f"[bold blue]{label}...[/bold blue]"):
            try:
                count = func(**kwargs)
                console.print(f"  [green]✓[/green] {label}: {count}")
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] {label}: {e}")

    console.print()
    _display_top_posts()


# ── Display ───────────────────────────────────────────────────────────────


@app.command()
def show():
    """Show top unposted posts."""
    _display_top_posts()


def _display_top_posts():
    """Display top unposted posts with formatting."""
    from sqlalchemy import select
    from ai_posts.db.engine import get_session
    from ai_posts.db.models import Post
    from ai_posts.config import settings

    session = get_session()
    try:
        stmt = (
            select(Post)
            .where(Post.posted == False)  # noqa: E712
            .order_by(Post.predicted_score.desc())
            .limit(settings.top_posts_output)
        )
        posts = session.execute(stmt).scalars().all()

        if not posts:
            console.print("[yellow]No unposted posts available. Run the pipeline first.[/yellow]")
            return

        console.rule("[bold green]Top Posts for Today[/bold green]")

        for i, post in enumerate(posts, 1):
            score_text = f"Score: {post.predicted_score:.1f}" if post.predicted_score else ""
            header = Text(f"Post #{i}  {score_text}", style="bold cyan")
            console.print()
            console.print(Panel(
                post.content,
                title=header,
                border_style="cyan",
                padding=(1, 2),
            ))

        console.print()
    finally:
        session.close()


# ── Stats ─────────────────────────────────────────────────────────────────


@app.command()
def stats():
    """Show pipeline statistics."""
    from sqlalchemy import select, func
    from ai_posts.db.engine import get_session
    from ai_posts.db.models import RawComment, Cluster, Insight, Angle, Hook, Post

    session = get_session()
    try:
        table = Table(title="Pipeline Stats", show_header=True, header_style="bold magenta")
        table.add_column("Stage", style="cyan")
        table.add_column("Count", justify="right", style="green")

        counts = {
            "Raw Comments": session.execute(select(func.count(RawComment.id))).scalar(),
            "  └ Embedded": session.execute(
                select(func.count(RawComment.id)).where(RawComment.embedding.isnot(None))
            ).scalar(),
            "Clusters": session.execute(select(func.count(Cluster.id))).scalar(),
            "Insights": session.execute(select(func.count(Insight.id))).scalar(),
            "Angles": session.execute(select(func.count(Angle.id))).scalar(),
            "Hooks": session.execute(select(func.count(Hook.id))).scalar(),
            "  └ Scored": session.execute(
                select(func.count(Hook.id)).where(Hook.weighted_score.isnot(None))
            ).scalar(),
            "Posts": session.execute(select(func.count(Post.id))).scalar(),
            "  └ Unposted": session.execute(
                select(func.count(Post.id)).where(Post.posted == False)  # noqa: E712
            ).scalar(),
        }

        for label, count in counts.items():
            table.add_row(label, str(count or 0))

        console.print()
        console.print(table)
        console.print()
    finally:
        session.close()


if __name__ == "__main__":
    app()
