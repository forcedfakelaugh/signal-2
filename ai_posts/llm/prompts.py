"""
LLM prompt templates for each pipeline stage.

Each function returns a (system_prompt, user_prompt) tuple.
Keeping prompts in one place makes iteration easy.
"""

from ai_posts.config import settings


def distill_cluster(comments: list[str]) -> tuple[str, str]:
    """Distill a cluster of comments into compressed human insights."""
    system = (
        "You are an audience psychology researcher. "
        "You find the real human emotions behind what people say online."
    )
    niche = settings.content_niche
    joined = "\n".join(f"- {c}" for c in comments)
    user = f"""Below are comments from real people, grouped by semantic similarity.

Your task:
Extract 3–5 sharp, uncomfortable insights from these comments.

Domain Constraint:
Only extract insights that are specifically relevant to {niche}. Ignore generic productivity or life advice themes.

Each insight MUST:
1. Be exactly 1 sentence.
2. Contain internal tension or conflict.
3. Reveal a hidden fear, contradiction, or "unspoken" truth.
4. Be specific to the speaker's identity or situation (no generic advice).

Bad insight: "People are worried about AI taking their jobs."
Good insight: "Senior engineers aren't afraid of AI coding; they're afraid that their 10 years of 'intuition' is being commoditized into a $20/month subscription."

Comments:
{joined}

Respond in JSON:
{{
  "insights": [
    {{
      "text": "the compressed human truth",
      "confidence": 0.0-1.0
    }}
  ]
}}"""
    return system, user



def generate_angles(insight_text: str) -> tuple[str, str]:
    """Generate narrative angles for an insight."""
    system = (
        "You are a viral content strategist who specializes in "
        "finding unexpected angles on common feelings."
    )
    user = f"""Given this human insight:
"{insight_text}"

Generate 4-5 distinct narrative angles a content creator could use to write about this.

Each angle should be a different framing:
- Contrarian: challenge the conventional wisdom about this insight
- Personal realization: a "lightbulb moment" where this truth became clear
- The Cost of Ignorance: what happens if you don't solve this pain point
- Founder perspective: why most products or schools fix the wrong part of this
- First-principles: break it down to why our brains/society work this way

Rules:
- NEVER hallucinate statistics or cite fake "recent studies".
- Focus on the tension: the gap between where someone is and where they want to be.

Respond in JSON:
{{
  "angles": [
    {{
      "frame_type": "contrarian|personal|cost|founder|first_principles",
      "text": "the angle in 1-2 sentences"
    }}
  ]
}}"""
    return system, user


def generate_hooks(angle_text: str, insight_text: str) -> tuple[str, str]:
    """Generate hook lines for an angle."""
    system = (
        "You are a copywriter who writes opening lines for social media posts. "
        "Your hooks stop the scroll. They are specific, surprising, and emotionally resonant. "
        "Never use clichés like 'Here's the thing' or 'Let me tell you something'."
    )
    user = f"""Insight: "{insight_text}"
Angle: "{angle_text}"

Write 7 different opening lines (hooks) for a Facebook/LinkedIn post based on this angle.

Rules:
- Each hook should be 1-2 sentences max
- Be specific, not vague
- Create curiosity or emotional tension
- No clickbait — the hook must be honest
- Vary the structure (question, statement, story opener, statistic, etc.)

Respond in JSON:
{{
  "hooks": [
    {{"text": "the hook line"}}
  ]
}}"""
    return system, user


def score_hooks(hooks: list[str]) -> tuple[str, str]:
    """Score hooks using the structured rubric."""
    system = (
        "You are a content performance analyst. "
        "You evaluate social media hooks with surgical precision. "
        "Be harsh — most hooks are mediocre."
    )
    hooks_list = "\n".join(f"{i+1}. {h}" for i, h in enumerate(hooks))
    user = f"""Score each hook on these dimensions (1-5 scale):

- curiosity: Does it make you want to read more?
- clarity: Is it immediately understandable?
- specificity: Does it avoid vague/generic language?
- emotional_weight: Does it hit an emotional nerve?
- contrarian: Does it challenge expectations?
- shareability: Would someone tag a friend or share this?

Hooks to score:
{hooks_list}

Respond in JSON:
{{
  "scores": [
    {{
      "hook_index": 1,
      "curiosity": 4,
      "clarity": 5,
      "specificity": 3,
      "emotional_weight": 4,
      "contrarian": 2,
      "shareability": 3
    }}
  ]
}}"""
    return system, user


def write_post(hook: str, insight: str, angle: str) -> tuple[str, str]:
    """Write a full post from a hook."""
    system = (
        "You are a thoughtful content creator who writes authentic social media posts. "
        "Your writing feels human — conversational, reflective, and real. "
        "You never sound like AI. You never use corporate language. "
        "You write like someone sharing a genuine realization with friends."
    )
    user = f"""Write a social media post using this hook, insight, and angle.

Hook (opening line): "{hook}"
Underlying insight: "{insight}"
Narrative angle: "{angle}"

Rules for High-Signal Content:
1. NEVER use fabricated statistics (e.g. "70% of people...").
2. NEVER use fake characters or generic names like 'Sarah' or 'John'.
3. NO generic AI metaphors (no firehoses, trains, or landscapes). Use specific, grounded examples.
4. Add TENSION. Content is interesting when there is a conflict or an unpopular truth.
5. NO "positive/motivational" endings. End with a sharp realization or a cold truth.

Structure:
1. Hook (use the one provided, verbatim)
2. 2-3 sentences of personal reflection or context - lead with a specific moment
3. The core insight, stated without fluff
4. A sharp closing thought (no "Together we can...")

Respond in JSON:
{{
  "content": "the full post text"
}}"""
    return system, user


def persona_rewrite(post: str) -> tuple[str, str]:
    """Lightweight persona rewrite — formatting and tone only."""
    system = (
        "You are an editor who cleans up social media posts to feel natural. "
        "You preserve the message but remove anything that sounds artificial."
    )
    user = f"""Rewrite this post to remove any remaining AI-style "safety" or "genericism".

Original:
{post}

The Goal: Make this sound like a sharp, opinionated founder/creator. 

Rules:
- DELETE any mention of "Recent studies", "70%", or "Surveys show".
- DELETE generic phrases like "Learning journey", "Embrace the journey", or "Navigate the landscape".
- Add punchiness: Use short sentences for impact.
- Ensure there is an "Unpopular Opinion" or "Hard Truth" in the text.
- Make line breaks feel natural (Facebook-style: short paragraphs, plenty of white space).
- Keep it under 150 words.

Respond in JSON:
{{
  "content": "the rewritten post"
}}"""
    return system, user
