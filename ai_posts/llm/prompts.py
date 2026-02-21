"""
LLM prompt templates for each pipeline stage.

Each function returns a (system_prompt, user_prompt) tuple.
Keeping prompts in one place makes iteration easy.
"""


def distill_cluster(comments: list[str]) -> tuple[str, str]:
    """Distill a cluster of comments into compressed human insights."""
    system = (
        "You are an audience psychology researcher. "
        "You find the real human emotions behind what people say online."
    )
    joined = "\n".join(f"- {c}" for c in comments)
    user = f"""Below are comments from real people, grouped by semantic similarity.

Your task:
1. Identify the core emotional truth or pain point these comments share.
2. Compress it into 1-2 sentences — a "human insight" that a content creator could build a post around.
3. Be specific, not generic. "People feel overwhelmed" is bad. "Mid-career developers feel like they're falling behind because the tooling changes faster than they can learn" is good.

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
- Contrarian: challenge the conventional wisdom
- Story-based: frame it as a personal narrative
- Data-backed: cite a trend or statistic (can be directional)
- Founder perspective: frame through a builder/creator lens
- First-principles: break it down to root causes

Respond in JSON:
{{
  "angles": [
    {{
      "frame_type": "contrarian|story|data|founder|first_principles",
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

Structure:
1. Hook (use the one provided, verbatim)
2. 2-3 sentences of personal reflection or context
3. The core insight, stated clearly
4. A takeaway or call to reflect (NOT a call to action)

Rules:
- Keep it under 200 words
- No hashtags
- No emojis
- No "What do you think?" endings
- Write in first person
- Sound like a real person, not a content creator

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
    user = f"""Rewrite this post to sound more natural and human.

Original:
{post}

Rules:
- Keep the same structure and message
- Remove any phrases that sound like AI wrote it
- Make line breaks feel natural (Facebook-style: short paragraphs, breathing room)
- Don't add hashtags or emojis
- Don't add a motivational ending
- Keep it under 200 words

Respond in JSON:
{{
  "content": "the rewritten post"
}}"""
    return system, user
