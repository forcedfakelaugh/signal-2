# AI Facebook Post Generator --- V2 Architecture (Taste Engine Edition)

## Philosophy Shift

V1 = Linear generator\
V2 = Adaptive Taste Engine

This system is no longer a simple pipeline. It becomes a feedback-driven
content intelligence system.

------------------------------------------------------------------------

# Core Principles

1.  Cluster before distill
2.  Score with structured rubric
3.  Enforce persona consistency
4.  Maintain long-term memory
5.  Optimize for signal, not volume

------------------------------------------------------------------------

# High-Level Architecture

raw_sources\
→ normalize\
→ embed\
→ cluster\
→ cluster scoring\
→ insight extraction\
→ angle generation\
→ hook generation\
→ structured scoring\
→ persona rewrite\
→ generic filter\
→ final ranking\
→ publish queue\
→ performance learning\
→ memory compression

------------------------------------------------------------------------

# Project Structure (V2)

ai_posts/

cli.py config.py

db/ schema.sql models.py

sources/ youtube.py reddit.py hn.py reviews.py

pipeline/ normalize.py embed.py cluster.py cluster_score.py distill.py
angle.py hook.py score.py persona.py generic_filter.py rank.py learn.py
reflect.py

memory/ patterns.json high_performers.json banned_angles.json
persona_rules.json scoring_weights.json

llm/ client.py prompts.py

utils/ embeddings.py filters.py

------------------------------------------------------------------------

# Stage 1 --- Multi-Source Collection

Command:

    ai-posts collect

Sources: - YouTube comments - Reddit niche subs - Hacker News - Amazon
reviews - Podcast transcripts

Goal: Cross-source signal blending to avoid tonal bias.

Frequency: Weekly, not daily.

------------------------------------------------------------------------

# Stage 2 --- Embeddings + Clustering

    ai-posts cluster

Steps: 1. Generate embeddings 2. Reduce dimensionality (optional) 3.
K-means or HDBSCAN clustering 4. Score clusters by: - volume - emotional
intensity - novelty - cross-source overlap

Output: Top 10--20 clusters only.

------------------------------------------------------------------------

# Stage 3 --- Insight Extraction

    ai-posts distill

Input: Top clusters

Output: 20--40 compressed "human truths"

Dedupe threshold: Similarity \> 0.9

------------------------------------------------------------------------

# Stage 4 --- Angle Engine

    ai-posts angles

For each insight: Generate 5--7 narrative frames.

Examples: - Contrarian - Story-based - Data-backed - Founder
perspective - First-principles breakdown

------------------------------------------------------------------------

# Stage 5 --- Hook Generation + Structured Scoring

    ai-posts hooks

Generate 10 hooks per angle.

Score each hook using structured rubric:

curiosity (1--5) clarity (1--5) specificity (1--5) emotional weight
(1--5) contrarian-ness (1--5) shareability (1--5)

Weighted score = configurable in memory/scoring_weights.json

Keep top 3 per insight.

------------------------------------------------------------------------

# Stage 6 --- Persona Lock

    ai-posts persona

Apply: - rewrite in voice - enforce structural preferences - remove
banned phrases - ensure tone consistency

Stored in: memory/persona_rules.json

------------------------------------------------------------------------

# Stage 7 --- Anti-Generic Filter

    ai-posts filter

Reject posts containing: - vague openers - cliché transitions -
corporate filler language

Auto-regenerate if flagged.

------------------------------------------------------------------------

# Stage 8 --- Final Ranking

    ai-posts rank

Score =

hook_score + persona_consistency + cluster_weight + timeliness_weight

Output: Top 5 daily posts.

------------------------------------------------------------------------

# Stage 9 --- Learning Loop

After posting:

    ai-posts learn

Record: - likes - comments - shares - saves - impressions

------------------------------------------------------------------------

# Stage 10 --- Weekly Reflection

    ai-posts reflect

1.  Cluster top 20% performers
2.  Detect structural patterns
3.  Update:
    -   scoring_weights.json
    -   banned_angles.json
    -   persona_rules.json

System becomes self-optimizing.

------------------------------------------------------------------------

# Orchestration

Single daily command:

    ai-posts today

Internally runs required stages. No multi-cron complexity.

------------------------------------------------------------------------

# Success Metrics

-   ≥ 2 posts/day you *want* to publish
-   20% increase in engagement month over month
-   Reduced AI "smell" over time
-   Increasing structural consistency

------------------------------------------------------------------------

# Evolution Path

After stability:

1.  Add timeliness detector
2.  Add topic momentum scoring
3.  Add collaborative critique mode
4.  Convert into SaaS creator OS

------------------------------------------------------------------------

# End State

This is no longer a content generator.

It becomes:

A personal narrative intelligence engine.
