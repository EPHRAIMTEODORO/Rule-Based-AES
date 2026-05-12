"""Prompt templates for local Llama 3 ESL rubric scoring."""

from __future__ import annotations


SYSTEM_PROMPT = """You are an ESL writing assessor. Score only the rubric traits requested. Be consistent, conservative, and evidence-based. Do not invent details that are not supported by the essay. If a criterion is unclear, give the lower score unless the essay clearly meets the higher level. Return valid JSON only."""


USER_PROMPT_TEMPLATE = """You are scoring a student ESL essay for placement.

Use this rubric:

Level 6:
- Clearly organized with cohesive devices used accurately
- Fully developed essay with 4 or more paragraphs
- Developed, concrete supporting detail, with some abstract elaboration
- Strong grammar control; only infrequent errors
- Easily understood by native readers unfamiliar with learner writing

Level 5:
- Clearly organized with some accurate cohesive devices
- 4 paragraphs
- Concrete supporting detail
- Moderate vocabulary and grammar control; errors do not block meaning
- Understandable with some effort

Level 4:
- Partially organized; cohesion is limited or inconsistent
- 2-3 paragraphs
- Personal and sometimes concrete detail
- Errors may distort meaning, though the essay is generally understandable

Level 3:
- Weak organization; ideas may be listed or loosely connected
- 1-2 paragraphs, or paragraphs are present but underdeveloped
- Limited, repetitive, or mostly general supporting detail
- Frequent grammar and vocabulary errors may distort meaning
- Understandable only with effort

Level 2:
- Minimal organization; ideas are difficult to follow
- Very limited development
- Little relevant support
- Frequent errors often block meaning
- Difficult for native readers unfamiliar with learner writing to understand

Level 1:
- Very limited, fragmentary, memorized, or mostly off-topic response
- Little or no development
- Meaning is mostly unclear
- Does not show enough control for Level 2

Task:
1. Score each LLM-handled criterion separately.
2. Give one LLM recommended score.
3. Briefly explain the evidence from the essay.

Important:
- Use paragraph_count from metadata for paragraph quantity.
- Judge paragraph_development based on whether the paragraphs are developed, not only whether they exist.
- Do not reward length alone.
- Do not assign Level 4 or higher unless the essay clearly meets the Level 4 descriptors.
- Do not assign Level 5 or higher unless organization, development, support, and comprehensibility are all clearly at that level.
- Do not penalize grammar twice: grammar_meaning_impact should measure whether errors interfere with meaning, not the number of errors.
- The final hybrid model will use separate rule-based grammar features.
- Do not quote long passages.
- Return valid JSON only.

Scoring scale:
- Trait scores must be integers from 1 to 6.
- llm_recommended_score may use half-points from 1.0 to 6.0.

Required JSON keys:
- essay_id
- organization
- paragraph_development
- supporting_detail
- abstract_elaboration
- prompt_control
- comprehensibility
- grammar_meaning_impact
- llm_recommended_score
- justification

Essay metadata:
- Essay ID: {essay_id}
- Essay prompt/topic: {prompt_id}
- Paragraph count: {paragraph_count}

Essay:
{essay_text}
"""


def build_user_prompt(
    essay_id: str,
    prompt_id: str,
    paragraph_count: int,
    essay_text: str,
) -> str:
    """Build the user prompt for one essay."""
    return USER_PROMPT_TEMPLATE.format(
        essay_id=essay_id,
        prompt_id=prompt_id or "Not provided",
        paragraph_count=paragraph_count,
        essay_text=essay_text,
    )
