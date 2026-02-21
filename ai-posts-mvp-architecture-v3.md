# AI Facebook Post Generator --- MVP Architecture (Signal-First Edition)

## Philosophy

This MVP is not a full self-optimizing taste engine.

It is a **signal validation engine**.

Goal: - Maximize upstream insight quality - Enforce structured hook
selection - Prevent repetition early - Avoid premature complexity

No learning loops. No auto weight tuning. No over-optimization.

Prove signal first.

------------------------------------------------------------------------

# Core MVP Principles

1.  Cluster before generating
2.  Score hooks with structure
3.  Enforce novelty via vector memory
4.  Keep persona lightweight
5.  Optimize for clarity over automation

------------------------------------------------------------------------

# Simplified High-Level Architecture

raw_sources\
→ normalize\
→ embed\
→ cluster\
→ cluster_score\
→ distill\
→ angle\
→ hook\
→ structured_score\
→ novelty_check\
→ persona_rewrite\
→ output_top_posts

------------------------------------------------------------------------

# Project Structure (MVP)

ai_posts/

cli.py\
config.py

db/\
schema.sql

sources/\
youtube.py\
reddit.py\
hn.py

pipeline/\
normalize.py\
embed.py\
cluster.py\
cluster_score.py\
distill.py\
angle.py\
hook.py\
score.py\
novelty.py\
persona.py\
rank.py

memory/\
past_posts_vectors.json\
scoring_weights.json\
persona_rules.json

llm/\
client.py\
prompts.py

utils/\
embeddings.py\
similarity.py

------------------------------------------------------------------------

# Stage 1 --- Multi-Source Collection

Command:

    ai-posts collect

Sources: - YouTube comments - Reddit niche subs - Hacker News

Frequency: Weekly batch (not daily).

Goal: Generate enough raw volume for meaningful clustering.

------------------------------------------------------------------------

# Stage 2 --- Embedding + Clustering

Command:

    ai-posts cluster

Steps:

1.  Generate embeddings for all normalized content
2.  Use HDBSCAN (no manual K tuning)
3.  Rank clusters by:
    -   size
    -   cross-source presence

Cluster Score (MVP):

cluster_score = w1 \* normalized_cluster_size + w2 \* cross_source_count

Output: Top 10--20 clusters only.

Keep this deterministic and simple.

------------------------------------------------------------------------

# Stage 3 --- Insight Distillation

Command:

    ai-posts distill

Input: Top ranked clusters

Output: 20--40 compressed human insights

Deduplication: Similarity threshold = 0.85

These insights become generation seeds.

------------------------------------------------------------------------

# Stage 4 --- Angle Engine

Command:

    ai-posts angles

For each insight: Generate 3--5 narrative frames:

-   Contrarian
-   Founder perspective
-   Data-backed
-   First-principles breakdown
-   Story framing

Keep angles simple and structured.

------------------------------------------------------------------------

# Stage 5 --- Hook Generation + Structured Scoring

Command:

    ai-posts hooks

Generate: 5--10 hooks per angle

Score each hook using structured rubric:

-   Curiosity (1--5)
-   Clarity (1--5)
-   Specificity (1--5)
-   Emotional weight (1--5)
-   Contrarian-ness (1--5)
-   Shareability (1--5)

Weighted score = sum(weight_i \* metric_i)

Keep top 3 per insight.

No auto weight updates yet.

------------------------------------------------------------------------

# Stage 6 --- Novelty Check (Critical MVP Component)

Before final ranking:

1.  Embed generated post
2.  Compare against vector memory of past posts
3.  Reject if cosine similarity \> 0.85

Memory file:

memory/past_posts_vectors.json

This prevents repetition and protects long-term signal quality.

------------------------------------------------------------------------

# Stage 7 --- Persona Rewrite (Light Version)

Command:

    ai-posts persona

Apply:

-   Tone alignment
-   Structural preferences
-   Remove obvious AI phrasing

Persona is formatting only in MVP. Not worldview enforcement yet.

------------------------------------------------------------------------

# Stage 8 --- Final Ranking

Command:

    ai-posts rank

Score =

hook_score + cluster_weight

Output: Top 3--5 posts for manual review.

Human decides what to publish.

------------------------------------------------------------------------

# What Is NOT Included In MVP

-   Weekly reflection loop
-   Auto weight tuning
-   Momentum scoring
-   Emotional intensity modeling
-   Exploration parameter
-   Timeliness detector
-   Banned angle evolution
-   SaaS abstraction layer

Those come after signal validation.

------------------------------------------------------------------------

# Success Criteria (MVP)

-   At least 2 posts/day you genuinely want to publish
-   Reduced AI "smell"
-   No noticeable repetition across 30+ posts
-   Consistent structural quality

------------------------------------------------------------------------

# Evolution Path After Validation

After 30--50 real posts:

1.  Add engagement tracking
2.  Add performance-based weight adjustment
3.  Introduce exploration factor (10--20% experimental posts)
4.  Add structural pattern mining from top performers
5.  Upgrade persona from formatting → worldview engine

------------------------------------------------------------------------

# End State (Post-MVP)

Validated signal engine → adaptive taste engine → creator OS.

But first:

Prove the signal.
