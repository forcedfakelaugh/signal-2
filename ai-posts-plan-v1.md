# AI Facebook Post Generator --- Implementation Plan (CLI-First)

## Goal (v1)

> Every morning run `ai-posts today` → get 5 posts you actually want to
> publish.

No UI. No automation posting.\
Just a tight feedback loop that builds taste.

------------------------------------------------------------------------

## System Pipeline

    collect → clean → distill → angle → hook → score → write → pick best → log results

Runs locally with cron + SQLite.

------------------------------------------------------------------------

## Tech Stack

**Language** - Python

**Libraries** - httpx --- API calls - pydantic --- schemas - sqlite3 ---
storage - typer --- CLI - rich --- terminal output - scikit-learn ---
clustering - sentence-transformers (or embedding API)

**LLM** - Model A: cheap/fast (generation) - Model B: smart
(critic/scoring)

------------------------------------------------------------------------

## Project Structure

    ai_posts/
      cli.py
      config.py

      db/
        schema.sql
        models.py

      sources/
        youtube.py
        reddit.py
        facebook.py

      pipeline/
        clean.py
        distill.py
        angle.py
        hook.py
        score.py
        write.py
        learn.py

      llm/
        client.py
        prompts.py

      utils/
        embeddings.py
        cluster.py
        filters.py

Keep synchronous first. No async complexity yet.

------------------------------------------------------------------------

## Database Schema

### comments

    id
    source
    text
    created_at
    collected_at

### insights

    id
    text
    created_at

### angles

    id
    insight_id
    text

### hooks

    id
    angle_id
    text
    score
    reason

### posts

    id
    hook_id
    content
    predicted_score
    created_at
    posted
    real_score

------------------------------------------------------------------------

# Phase 1 --- Data Collection

Command:

    ai-posts collect youtube

Filter: - contains "I" or "we" - \> 8 words - not URL/spam

Goal: 500--2000 comments

------------------------------------------------------------------------

# Phase 2 --- Distillation

    ai-posts distill

Batch comments → LLM → pain statements → dedupe similarity \> 0.9

Goal: 20--60 real human truths

------------------------------------------------------------------------

# Phase 3 --- Angles

    ai-posts angles

Generate 5 angles per insight.

------------------------------------------------------------------------

# Phase 4 --- Hooks + Scoring

    ai-posts hooks

Generate 10 hooks → score → keep top 3.

------------------------------------------------------------------------

# Phase 5 --- Write Posts

    ai-posts write

Structure: Hook\
3 sentence reflection\
1 insight\
1 takeaway

Style reference: examples/me.txt

------------------------------------------------------------------------

# Phase 6 --- Daily Command

    ai-posts today

Show top 5 unposted posts.

------------------------------------------------------------------------

# Phase 7 --- Learning Loop

After posting:

    ai-posts learn

Record engagement.

Weekly:

    ai-posts reflect

Update memory rules.

------------------------------------------------------------------------

# Cron Schedule

    08:00 collect
    08:10 distill
    08:20 angles
    08:30 hooks
    08:40 write

------------------------------------------------------------------------

# Success Criteria

Only automate posting when you naturally want to publish ≥2/day.

------------------------------------------------------------------------

# Result After 2 Weeks

-   Personal taste dataset
-   Audience psychology memory
-   Repeatable idea discovery engine
