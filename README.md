# Signal-2: AI Post Generator

A **signal-first content generation pipeline** that mines real human emotions from online comments, clusters them into insights, and produces authentic social media posts — all from the command line.

The system doesn't generate content from thin air. It listens to what real people are saying, finds the patterns, and turns those patterns into posts you'd actually want to publish.

---

## How It Works

```
raw comments → embed → cluster → distill → angles → hooks → score → write → posts
```

| Stage | What happens |
|---|---|
| **Collect** | Pull comments from YouTube videos/channels (Reddit, HN planned) |
| **Embed** | Generate vector embeddings for every comment |
| **Cluster** | Group similar comments using HDBSCAN (no manual K tuning) |
| **Distill** | LLM extracts compressed "human truths" from top clusters |
| **Angles** | Generate 4–5 narrative frames per insight (contrarian, story, data, etc.) |
| **Hooks** | Create 7 hook lines per angle, scored on a 6-dimension rubric |
| **Write** | Compose full posts from top hooks with persona rewrite |
| **Novelty** | Reject posts too similar to past output (cosine similarity > 0.85) |

Every stage is **idempotent** — safe to re-run without duplicating data.

---

## Architecture

```
┌─────────────────────────────────────┐
│          CLI (Typer + Rich)         │
├─────────────────────────────────────┤
│         Pipeline Stages             │
│  collect → embed → cluster →        │
│  distill → angle → hook → write     │
├──────────────────┬──────────────────┤
│   LLM Client     │   Sources        │
│   (OpenAI SDK)   │   (YouTube API)  │
├──────────────────┴──────────────────┤
│     SQLAlchemy + pgvector           │
├─────────────────────────────────────┤
│     Neon Postgres (serverless)      │
└─────────────────────────────────────┘
```

**Key design decisions:**
- **pgvector** for embeddings — novelty checks and dedup are single SQL queries, not Python loops
- **Neon Postgres** — serverless, free tier, zero infrastructure management
- **OpenRouter** — access free and paid LLMs through one API
- **Pydantic models everywhere** — typed contracts between all pipeline stages
- **Lazy imports in CLI** — instant startup despite heavy ML dependencies

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| CLI | [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) |
| Database | [Neon Postgres](https://neon.tech/) (serverless) |
| Vector Search | [pgvector](https://github.com/pgvector/pgvector) |
| ORM | [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| LLM | [OpenAI SDK](https://github.com/openai/openai-python) (compatible with OpenRouter, Groq, Together, etc.) |
| Embeddings | `text-embedding-3-small` via OpenRouter |
| Clustering | [HDBSCAN](https://hdbscan.readthedocs.io/) |
| HTTP | [httpx](https://www.python-httpx.org/) |

---

## Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd signal-2

# Create virtual environment (Python 3.11+ required)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Neon Postgres connection string
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require

# LLM provider (OpenRouter example with free model)
OPENAI_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_FAST=arcee-ai/trinity-large-preview:free
LLM_MODEL_SMART=arcee-ai/trinity-large-preview:free

# Embeddings
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# YouTube Data API v3
YOUTUBE_API_KEY=AIza...
```

### 3. Initialize Database

```bash
ai-posts init-db
```

This enables the pgvector extension and creates all tables.

### 4. Run the Pipeline

```bash
# Collect comments from a YouTube video
ai-posts collect youtube VIDEO_ID --max 500

# Run stages individually
ai-posts embed
ai-posts cluster --min-size 5
ai-posts distill
ai-posts angles
ai-posts hooks
ai-posts write

# Or run everything at once
ai-posts today

# View results
ai-posts show
ai-posts stats
```

---

## CLI Reference

| Command | Description |
|---|---|
| `ai-posts init-db` | Create database tables + enable pgvector |
| `ai-posts collect youtube <ID>` | Collect comments from a YouTube video or channel |
| `ai-posts embed` | Generate embeddings for un-embedded comments |
| `ai-posts cluster [--min-size N]` | Cluster comments using HDBSCAN |
| `ai-posts distill` | Distill top clusters into human insights |
| `ai-posts angles` | Generate narrative angles for each insight |
| `ai-posts hooks` | Generate and score hooks (6-dimension rubric) |
| `ai-posts write` | Write full posts with persona rewrite + novelty check |
| `ai-posts today` | Run the full pipeline end-to-end |
| `ai-posts show` | Display top unposted posts |
| `ai-posts stats` | Show pipeline statistics table |

**Tip:** Channel IDs starting with `UC` are auto-detected — `ai-posts collect youtube UCxxxx` will collect from the channel's recent videos.

---

## Project Structure

```
signal-2/
├── pyproject.toml              # Dependencies & CLI entry point
├── .env                        # Local configuration (git-ignored)
├── .env.example                # Template for .env
│
└── ai_posts/
    ├── config.py               # Pydantic settings from environment
    │
    ├── db/
    │   ├── engine.py           # SQLAlchemy engine & session factory
    │   └── models.py           # ORM models with pgvector columns
    │
    ├── llm/
    │   ├── client.py           # generate() / smart_generate() / embed()
    │   └── prompts.py          # All LLM prompt templates
    │
    ├── pipeline/
    │   ├── collect.py          # Source ingestion with upsert
    │   ├── embed.py            # Batch embedding generation
    │   ├── cluster.py          # HDBSCAN clustering + scoring
    │   ├── distill.py          # Insight extraction + dedup
    │   ├── angle.py            # Narrative angle generation
    │   ├── hook.py             # Hook generation + structured scoring
    │   └── write.py            # Post writing + persona + novelty
    │
    ├── sources/
    │   └── youtube.py          # YouTube Data API v3 collector
    │
    └── cli.py                  # Typer CLI commands
```

---

## Database Schema

Seven tables in Postgres with pgvector:

```
raw_comments ──┐
               ├── cluster_items ── clusters
               │
               └── (embeddings stored as vector(1536))

clusters ── insights ── angles ── hooks ── posts
                │                           │
                └── embedding              └── embedding
                    (dedup)                    (novelty check)
```

| Table | Purpose | Key columns |
|---|---|---|
| `raw_comments` | Source material | `text`, `source`, `source_id`, `embedding` |
| `clusters` | HDBSCAN groupings | `size`, `cross_source_count`, `score` |
| `cluster_items` | Comment ↔ Cluster mapping | `cluster_id`, `comment_id` |
| `insights` | Distilled human truths | `text`, `embedding`, `cluster_id` |
| `angles` | Narrative frames | `frame_type`, `text`, `insight_id` |
| `hooks` | Opening lines + scores | 6 score dimensions + `weighted_score` |
| `posts` | Final generated content | `content`, `embedding`, `predicted_score`, `posted` |

---

## Hook Scoring Rubric

Every hook is scored on 6 dimensions (1–5 scale):

| Dimension | Weight | What it measures |
|---|---|---|
| Curiosity | 1.0 | Does it make you want to read more? |
| Clarity | 1.0 | Is it immediately understandable? |
| Specificity | 1.2 | Does it avoid vague/generic language? |
| Emotional weight | 1.0 | Does it hit an emotional nerve? |
| Contrarian-ness | 0.8 | Does it challenge expectations? |
| Shareability | 1.0 | Would someone share this? |

Weights are configurable via environment variables (`WEIGHT_CURIOSITY`, `WEIGHT_CLARITY`, etc.).

---

## Configuration Reference

All settings are configured via environment variables or `.env` file:

### Required

| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon Postgres connection string |
| `OPENAI_API_KEY` | API key (works with OpenAI, OpenRouter, etc.) |

### Optional

| Variable | Default | Description |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API endpoint |
| `LLM_MODEL_FAST` | `gpt-4o-mini` | Model for content generation |
| `LLM_MODEL_SMART` | `gpt-4o` | Model for scoring/critique |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `1536` | Embedding vector size |
| `YOUTUBE_API_KEY` | — | YouTube Data API v3 key |
| `NOVELTY_THRESHOLD` | `0.85` | Cosine similarity cutoff for novelty |
| `TOP_CLUSTERS` | `15` | Max clusters to process |
| `TOP_POSTS_OUTPUT` | `5` | Number of posts to generate |

---

## Using Free Models

This project runs entirely on free infrastructure:

| Service | Free tier |
|---|---|
| **Neon Postgres** | 0.5 GB storage, 191 compute hours/month |
| **OpenRouter** | Free models (e.g., `arcee-ai/trinity-large-preview:free`) |
| **YouTube Data API** | 10,000 units/day |

To use OpenRouter free models, set in `.env`:

```env
OPENAI_API_KEY=sk-or-v1-your-key
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL_FAST=arcee-ai/trinity-large-preview:free
LLM_MODEL_SMART=arcee-ai/trinity-large-preview:free
EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

## Deployment

The CLI runs locally or on any server with Python. For automated scheduling:

### Cron (VPS)

```bash
# Weekly collection + daily generation
0 8 * * 1  cd /path/to/signal-2 && .venv/bin/ai-posts collect youtube VIDEO_ID
0 9 * * *  cd /path/to/signal-2 && .venv/bin/ai-posts today
```

### GitHub Actions

```yaml
on:
  schedule:
    - cron: '0 8 * * *'
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install -e .
      - run: ai-posts today
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Future: Web Dashboard

Since the database is on Neon, a Next.js frontend on Vercel can read the same data:

```
Python CLI (VPS/cron) ──┐
                        ├── Neon Postgres
Next.js UI (Vercel)  ───┘
```

---

## Evolution Roadmap

This MVP validates signal quality. After 30–50 real posts:

- [ ] Add Reddit and Hacker News sources
- [ ] Engagement tracking (`ai-posts learn`)
- [ ] Performance-based weight adjustment
- [ ] Exploration factor (10–20% experimental posts)
- [ ] Structural pattern mining from top performers
- [ ] Persona upgrade: formatting → worldview engine
- [ ] Web dashboard for post review and publishing

---

## License

Private project.
