"""Prompt templates for local Llama 3 ESL rubric scoring."""

from __future__ import annotations


SYSTEM_PROMPT = """You are an ESL writing assessor. Score only the rubric traits requested. Be consistent, conservative, and evidence-based. Do not invent details that are not supported by the essay. If a criterion is unclear, give the lower score unless the essay clearly meets the higher level. Return valid JSON only."""


LEVEL_6_ANCHOR = """Distance, expense, comfort, structure, security, accessibility, and people are some of the things most students consider when choosing a place to live while studying. For instance, I debated with my mom a lot about living arrangements when I was in high school because I want to live at the dorm and while she wants me to stay at home. Now that I will be a college student, I prefer living in apartments in the community so that I can be independent in all aspects of my life.

Having an apartment, provides opportunities to accumulate knowledge based on experience. Budgeting money, time, and energy are best learned through situations that challenges a person. I think that living alone or even with 1 or 2 others, will push me to be more independent. For example, I only learned to be smart in buying groceries when I volunteered as a missionary and lived with one other person.

Another reason is that the distance can improve physical health. Normally, I don't like running. However, if there is a place that offers fresh air and new sights? I will be motivated to jog and take long walks every day. This allows me to take charge of my body.

Being outside the campus, expands social circles. All students are busy and occupied. Having different neighbors who are not all students promotes diversity. Having different kinds of neighbors reminds me of being home, thus preventing homesickness and moments of being alone. Another bonus is the joy one can receive through the opportunities to serve others.

Finally, living in an apartment nurtures emotional resilience. I learned to step out of my comfort zone as I live in an apartment. I love my personal time, but what I appreciate most about living in an apartment is that I have the opportunity to practice trusting myself.

To conclude, there are many factors to consider when a college student decides whether to live in the dorms or at home. It is important to consider distance, expense, comfort, structure, security, accessibility and personal interactions. If one takes into consideration each one of these and explores them thoroughly, he/she should be fine with the decision made."""


LEVEL_5_ANCHOR = """It has been very common for student to live out of their house when studying in a university, most specially when the University is away from home. I have never experienced living inside a university dormitory, but I have already tried living in a apartment when I was still serving a mission. According to my friends who stays in a university apartment, it can be fun sometimes, as long as you get along with those people you stay with the dormitory, and you can gain friends from other departments also. But on the other side, it can sometimes be hassle if you want space and a time for yourself to study, and there will be more people that you will be living with than living in a apartment where you can choose to be alone or have just few people that you know to live with you. Living in a apartment is nice if you want to have a more private life and a more peaceful surrounding. And it is a different experience from living in a university dormitory.

For me, I would prefer to live in an apartment in the community. Connected to what I said in the first paragraph, having your own apartment can create freedom and privacy for me. As to freedom, I do like to make my own rules inside the house, for example, I don't like to stay in a room or house that is messy, I do like to clean a lot, and it bothers me a lot if the house is dirty. Also, I can invite whoever I want, either friends or family. For privacy, as much I want to be around by a lot of people, I love to have my own personal time. There will be times that I need to be alone, most specially when I am studying, I don't want anything that can really disturb my study time, and also, I have time to ponder and meditate on important things that I need to prioritize. Freedom and privacy gives me the peace to where I live.

Since growing up in my parents house, I did not have much of the privacy that I needed, since I have my siblings with me, they would just barge my room anytime they want, or they just enter my room and take my own things without my permission. And I am that kind of person who loves her personal time and someone whom you need to ask permission with things you want to borrow or take. I live to have a peaceful mind and to stay connected with the Lord, so having my own apartment will give me the ease that I need. This also gives me the idea of having the feeling of being at home, since I can make it my own home, than having to share a room with people I just met. I love being around people, but trusting people immediately is not really my thing. Therefore, living on my own in a apartment will be easier for me, and in there I can just bring friends without any restrictions to follow, since university dormitories have rules and regulations where I know I am not at best in following, most specially when being out late with friends and I am not good at keeping time.

Upon with choosing which to live in, being in a university dormitory is really not bad, since it can create friendship with other people. But for me, living in a apartment will give me the feeling of being at ease and safe. Since I have already experienced living in a apartment when I served a mission, it gives me more of the idea what it feels to live in a apartment, can be somewhat being in a university dormitory, since I was able to live with 2 to 4 people in a apartment. With regards to that, I am more contented in having my own apartment and don't have too much to worry with my own privacy and peace in living outside of my parent's house. And there, I can be comfortable as much as I want, be myself often, not fearing of what other people might say to me or the actions I will do. Choosing to live in an apartment is for my own comfort and convenience."""


LEVEL_4_ANCHOR = """Each of us has a agency and we have freedom to choose, that's why I truly understand that some students may choose to live in universities dormitories and some may choose to live in apartments in the community. In my case, I would choose living in university dormitories, because there are some things that can be control and you will be protected from any dangers and temptations. For me living inside the campus can offer some unique benefits that will help you focus on your studies.

There are some particular reasons why I've chosen this because you are close to all school facilities and that makes convenient, making easy to attend classes, access resources , and participate in school activities. Living on campus can provide a structured environment prior to studying, with easy access to libraries and quiet study areas. You may find peace and you can focus more on your task and activities , this also can help you more prepared in any test or exams you have because you can study peacefully. A school like BYU- HAWAII is a great example because if you choose to live inside their campus , they assure your safety and can protect you from temptations through having spiritual activities that can guide you to a righteous path. BYU- HAWAII truly can help you focus on your covenant path while studying.

Lastly, living in university dormitories, can provide you a sense of safety and a peace of mind. It will protect you against dangers outside the school, and can help you prioritize more your studies that can help you become successful in your career."""


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

Use these anchor essays as calibration examples:

Level 6 anchor:
{level_6_anchor}

Level 5 anchor:
{level_5_anchor}

Level 4 anchor:
{level_4_anchor}

Task:
1. Score each LLM-handled criterion separately.
2. Give one LLM recommended score.
3. Briefly explain the evidence from the essay.

Important:
- Use the anchor essays to calibrate the score. Compare the target essay's organization, development, detail, control, and comprehensibility against the anchors.
- Do not copy language from the anchor essays into the justification.
- Do not reward an essay only because it has the same topic as an anchor.
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
        level_6_anchor=LEVEL_6_ANCHOR,
        level_5_anchor=LEVEL_5_ANCHOR,
        level_4_anchor=LEVEL_4_ANCHOR,
    )
