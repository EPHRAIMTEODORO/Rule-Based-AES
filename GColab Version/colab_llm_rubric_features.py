"""Extract selected LLM rubric features with local Ollama Llama 3.

This script is intentionally focused on discourse and task-response traits:
organization/coherence, paragraph development, supporting detail/elaboration,
comprehensibility, and prompt fulfillment.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import pandas as pd


TEXT_COLUMN_CANDIDATES = [
    "essay",
    "text",
    "text_clean",
    "essay_text",
    "response",
    "answer",
]

LLM_TRAIT_COLUMNS = [
    "llm_paragraph_count",
    "llm_performance_band",
    "llm_organization_coherence",
    "llm_paragraph_development",
    "llm_supporting_detail_elaboration",
    "llm_comprehensibility",
    "llm_prompt_fulfillment",
    "llm_overall_score",
    "llm_justification",
]

SYSTEM_PROMPT = """You are an ESL writing assessor. Evaluate only the requested rubric traits. Be consistent, conservative, and evidence-based. Do not invent details that are not supported by the essay. Return valid JSON only."""

LEVEL_6_ANCHOR = """Distance, expense, comfort, structure, security, accessibility, and people are some of the things most students consider when choosing a place to live while studying. For instance, I debated with my mom a lot about living arrangements when I was in high school because I want to live at the dorm and while she wants me to stay at home. Now that I will be a college student, I prefer living in apartments in the community so that I can be independent in all aspects of my life.

Having an apartment, provides opportunities to accumulate knowledge based on experience. Budgeting money, time, and energy are best learned through situations that challenges a person. I think that living alone or even with 1 or 2 others, will push me to be more independent. For example, I only learned to be smart in buying groceries when I volunteered as a missionary and lived with one other person.

Another reason is that the distance can improve physical health. Normally, I don't like running. However, if there is a place that offers fresh air and new sights? I will be motivated to jog and take long walks every day. This allows me to take charge of my body.

Being outside the campus, expands social circles. All students are busy and occupied. Having different neighbors who are not all students promotes diversity. Having different kinds of neighbors reminds me of being home, thus preventing homesickness and moments of being alone. Another bonus is the joy one can receive through the opportunities to serve others.

Finally, living in an apartment nurtures emotional resilience. I learned to step out of my comfort zone as I live in an apartment. I love my personal time, but what I appreciate most about living in an apartment is that I have the opportunity to practice trusting myself.

To conclude, there are many factors to consider when a college student decides whether to live in the dorms or at home. It is important to consider distance, expense, comfort, structure, security, accessibility and personal interactions. If one takes into consideration each one of these and explores them thoroughly, he/she should be fine with the decision made."""

LEVEL_5_ANCHOR = """It has been very common for student to live out of their house when studying in a university, most specially when the University is away from home. I have never experienced living inside a university dormitory, but I have already tried living in a apartment when I was still serving a mission. According to my friends who stays in a university apartment, it can be fun sometimes, as long as you get along with those people you stay with the dormitory, and you can gain friends from other departments also. But on the other side, it can sometimes be hassle if you want space and a time for yourself to study, and there will be more people that you will be living with than living in a apartment where you can choose to be alone or have just few people that you know to live with you. Living in a apartment is nice if you want to have a more private life and a more peaceful surrounding. And it is a different experience from living in a university dormitory.

For me, I would prefer to live in an apartment in the community. Connected to what I said in the first paragraph, having your own apartment can create freedom and privacy for me. As to freedom, I do like to make my own rules inside the house, for example, I don't like to stay in a room or house that is messy, I do like to clean a lot, and it bothers me a lot if the house is dirty. Also, I can invite whoever I want, either friends or family. For privacy, as much I want to be around by a lot of people, I love to have my own personal time. There will be times that I need to be alone, most specially when I am studying, I don't want anything that can really disturb my study time, and also, I have time to ponder and meditate on important things that I need to prioritize. Freedom and privacy gives me the peace to where I live. Since growing up in my parents house, I did not have much of the privacy that I needed, since I have my siblings with me, they would just barge my room anytime they want, or they just enter my room and take my own things without my permission. And I am that kind of person who loves her personal time and someone whom you need to ask permission with things you want to borrow or take. I live to have a peaceful mind and to stay connected with the Lord, so having my own apartment will give me the ease that I need. This also gives me the idea of having the feeling of being at home, since I can make it my own home, than having to share a room with people I just met. I love being around people, but trusting people immediately is not really my thing. Therefore, living on my own in a apartment will be easier for me, and in there I can just bring friends without any restrictions to follow, since university dormitories have rules and regulations where I know I am not at best in following, most specially when being out late with friends and I am not good at keeping time.

Upon with choosing which to live in, being in a university dormitory is really not bad, since it can create friendship with other people. But for me, living in a apartment will give me the feeling of being at ease and safe. Since I have already experienced living in a apartment when I served a mission, it gives me more of the idea what it feels to live in a apartment, can be somewhat being in a university dormitory, since I was able to live with 2 to 4 people in a apartment. With regards to that, I am more contented in having my own apartment and don't have too much to worry with my own privacy and peace in living outside of my parent's house. And there, I can be comfortable as much as I want, be myself often, not fearing of what other people might say to me or the actions I will do. Choosing to live in an apartment is for my own comfort and convenience."""

LEVEL_4_ANCHOR = """Each of us has a agency and we have freedom to choose, that's why I truly understand that some students may choose to live in universities dormitories and some may choose to live in apartments in the community. In my case, I would choose living in university dormitories, because there are some things that can be control and you will be protected from any dangers and temptations. For me living inside the campus can offer some unique benefits that will help you focus on your studies.

There are some particular reasons why I've chosen this because you are close to all school facilities and that makes convenient, making easy to attend classes, access resources, and participate in school activities. Living on campus can provide a structured environment prior to studying, with easy access to libraries and quiet study areas. You may find peace and you can focus more on your task and activities, this also can help you more prepared in any test or exams you have because you can study peacefully. A school like BYU- HAWAII is a great example because if you choose to live inside their campus, they assure your safety and can protect you from temptations through having spiritual activities that can guide you to a righteous path. BYU- HAWAII truly can help you focus on your covenant path while studying.

Lastly, living in university dormitories, can provide you a sense of safety and a peace of mind. It will protect you against dangers outside the school, and can help you prioritize more your studies that can help you become successful in your career."""

LEVEL_3_ANCHOR = """In the most obvious sense, the main reason why most students decided to study abroad is due to limited resources and opportunities offered in schools in their countries.

For instance, unlike first world countries that have well-structured educational system, third world countries do not have all the required resources necessary for the success of a student in their education.

Due to this lack of resources and opportunities to help one succeed their education, students from particularly third world countries, decided to look for opportunities elsewhere abroad to further their education and acquire the vital skills necessary for their future careers.

Furthermore, over the years studies have shown that studying abroad has greatly benefited international students, because it provides new learning experiences and environment that improves their learning ability and therefore succeed in their studies. This is why most students study abroad."""

LEVEL_2_ANCHOR = """Why do students study abroad? student wants to study abroad because of the educational level of understanding in their own country is not suitable for them.

One of the reasons why student go abroad for study is because to have better Job opportunities, and also to have the higher level of education such as Degree and Phd that other country officers.

to conclude student go for schools and offer opportunity for student to able to provide for their school fees and offer education that help them to get jobs."""

LEVEL_1_ANCHOR = """There are several reasons for deciding between them. Apartments might seem much comfortable for having a quiet and good night sleep, but maybe they could be too far away from the campus and if I dont have the money for transportation then it will be difficult for me.

University dormtories will have a great advantage for being close to the schools and having roomates who might take the same classes as you do,

so I would prefer to live in a campus dormitory."""

USER_PROMPT_TEMPLATE = """Score this student ESL essay on five traits and one overall score.

Use integer scores from 1 to 6:
1 = very limited, difficult to understand, minimal development
2 = weak, partially understandable, limited support
3 = developing, generally understandable but inconsistent development
4 = adequate, clear organization and sufficient support
5 = strong, well developed and easy to follow
6 = excellent, highly developed, coherent, and consistently effective

Before assigning numeric scores, first classify the essay's overall performance
as one of these broad bands:
- Low
- Developing
- Adequate
- Strong
- Excellent

Then convert that broad judgment into the 1-6 scale. Use the broad band to
stabilize the final overall_score, but still assign each trait score based on
the specific evidence for that trait.

Traits to score:

1. organization_coherence
Evaluate whether the essay is clearly organized, ideas progress logically,
cohesion is effective, and the structure is easy to follow.

2. paragraph_development
Evaluate whether paragraphs are fully developed, ideas are elaborated
sufficiently, and development extends beyond minimal support. Use the paragraph
count as metadata, but judge quality of development rather than paragraph count
alone.

3. supporting_detail_elaboration
Evaluate whether examples are concrete, support is sufficiently developed, and
ideas are elaborated beyond surface-level statements.

4. comprehensibility
Evaluate whether the essay is easily understood by native readers unfamiliar
with non-native writing, how much effort interpretation requires, and the
overall communicative clarity.

5. prompt_fulfillment
Evaluate whether the essay addresses the assigned prompt, whether the response
is complete, and whether the content is relevant to the task.

Use these anchor essays to calibrate the 1-6 scale:

Level 6 anchor:
{level_6_anchor}

Level 5 anchor:
{level_5_anchor}

Level 4 anchor:
{level_4_anchor}

Level 3 anchor:
{level_3_anchor}

Level 2 anchor:
{level_2_anchor}

Level 1 anchor:
{level_1_anchor}

Important:
- Use the anchor essays only for score calibration.
- Do not copy language from the anchor essays into the justification.
- Do not reward or penalize the target essay only because it has a different
  topic from an anchor essay.
- Do not score grammar error frequency directly.
- Do not reward length alone.
- If evidence is mixed, choose the score that best represents the overall
  performance.
- Return JSON only.

Required JSON keys:
- performance_band
- organization_coherence
- paragraph_development
- supporting_detail_elaboration
- comprehensibility
- prompt_fulfillment
- overall_score
- justification

Essay metadata:
- Essay ID: {essay_id}
- Prompt/topic: {prompt_id}
- Paragraph count: {paragraph_count}

Essay:
{essay_text}
"""


def normalize_cell(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    replacements = {
        "\u00c2\u00a0": " ",
        "\u00a0": " ",
        "\u202f": " ",
        "\u2007": " ",
        "\ufeff": "",
        "¬†": " ",
    }
    for bad_value, replacement in replacements.items():
        text = text.replace(bad_value, replacement)
    return text.strip()


def choose_column(columns: list[str], explicit: Optional[str], candidates: list[str]) -> str:
    if explicit:
        if explicit not in columns:
            raise ValueError(f"Input file does not contain column: {explicit}")
        return explicit

    lowered_to_original = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in lowered_to_original:
            return lowered_to_original[candidate]

    raise ValueError(
        "Could not infer text column. "
        f"Use --text-column with one of: {', '.join(columns)}"
    )


def paragraph_count(text: str) -> int:
    cleaned = normalize_cell(text)
    if not cleaned:
        return 0

    blocks = [
        block.strip()
        for block in re.split(r"(?:\r?\n\s*){2,}", cleaned)
        if block.strip()
    ]
    if blocks:
        return len(blocks)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return len(lines) if lines else 1


def clamp_int_score(value: object, min_value: int = 1, max_value: int = 6) -> int:
    try:
        numeric = int(round(float(value)))
    except (TypeError, ValueError):
        return min_value
    return max(min_value, min(max_value, numeric))


def normalize_performance_band(value: object) -> str:
    text = normalize_cell(value).lower()
    valid_bands = {
        "low": "Low",
        "developing": "Developing",
        "adequate": "Adequate",
        "strong": "Strong",
        "excellent": "Excellent",
    }
    return valid_bands.get(text, "Low")


def extract_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object.")
    return json.loads(match.group(0))


def build_user_prompt(
    essay_id: str,
    prompt_id: str,
    paragraph_total: int,
    essay_text: str,
) -> str:
    return USER_PROMPT_TEMPLATE.format(
        essay_id=essay_id or "Not provided",
        prompt_id=prompt_id or "Not provided",
        paragraph_count=paragraph_total,
        essay_text=essay_text,
        level_6_anchor=LEVEL_6_ANCHOR,
        level_5_anchor=LEVEL_5_ANCHOR,
        level_4_anchor=LEVEL_4_ANCHOR,
        level_3_anchor=LEVEL_3_ANCHOR,
        level_2_anchor=LEVEL_2_ANCHOR,
        level_1_anchor=LEVEL_1_ANCHOR,
    )


def call_ollama_chat(
    system_prompt: str,
    user_prompt: str,
    model: str,
    ollama_url: str,
    temperature: float,
    timeout_seconds: int,
    retries: int,
    retry_delay_seconds: float,
) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": temperature},
    }
    request = urllib.request.Request(
        ollama_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    last_error = None
    for attempt in range(1, retries + 2):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            last_error = RuntimeError(f"Ollama HTTP {exc.code}: {error_body}")
        except urllib.error.URLError as exc:
            last_error = RuntimeError(
                f"Could not reach Ollama at {ollama_url}. Make sure Ollama is running "
                f"and the model is available with: ollama run {model}"
            )
        except (TimeoutError, socket.timeout) as exc:
            last_error = RuntimeError(
                f"Ollama request timed out after {timeout_seconds} seconds."
            )

        if attempt <= retries:
            print(
                f"Ollama call failed on attempt {attempt}; retrying in "
                f"{retry_delay_seconds:g}s",
                flush=True,
            )
            time.sleep(retry_delay_seconds)
        else:
            raise last_error

    content = response_payload.get("message", {}).get("content", "")
    if not content:
        raise ValueError(f"Ollama returned no message content: {response_payload}")
    return extract_json_object(content)


def normalize_llm_result(raw_result: dict) -> dict:
    return {
        "llm_performance_band": normalize_performance_band(
            raw_result.get("performance_band")
        ),
        "llm_organization_coherence": clamp_int_score(
            raw_result.get("organization_coherence")
        ),
        "llm_paragraph_development": clamp_int_score(
            raw_result.get("paragraph_development")
        ),
        "llm_supporting_detail_elaboration": clamp_int_score(
            raw_result.get("supporting_detail_elaboration")
        ),
        "llm_comprehensibility": clamp_int_score(raw_result.get("comprehensibility")),
        "llm_prompt_fulfillment": clamp_int_score(raw_result.get("prompt_fulfillment")),
        "llm_overall_score": clamp_int_score(raw_result.get("overall_score")),
        "llm_justification": normalize_cell(raw_result.get("justification", "")),
    }


def evaluate_row(row: pd.Series, args: argparse.Namespace, text_column: str, index: int) -> dict:
    essay_text = normalize_cell(row.get(text_column, ""))
    essay_id = normalize_cell(row.get(args.essay_id_column, "")) or f"essay_{index}"
    prompt_id = normalize_cell(row.get(args.prompt_column, "")) if args.prompt_column else ""
    paragraph_total = paragraph_count(essay_text)

    user_prompt = build_user_prompt(
        essay_id=essay_id,
        prompt_id=prompt_id,
        paragraph_total=paragraph_total,
        essay_text=essay_text,
    )
    raw_result = call_ollama_chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        model=args.model,
        ollama_url=args.ollama_url,
        temperature=args.temperature,
        timeout_seconds=args.timeout,
        retries=args.retries,
        retry_delay_seconds=args.retry_delay_seconds,
    )

    return {
        args.essay_id_column: essay_id,
        "llm_paragraph_count": paragraph_total,
        **normalize_llm_result(raw_result),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract selected LLM rubric features from essay XLSX/CSV files."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="NewAes/ELAT_DATA/essays.xlsx",
        help="Input .xlsx or .csv file. Defaults to NewAes/ELAT_DATA/essays.xlsx.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="NewAes/ELAT_DATA/llm_rubric_features.xlsx",
        help="Output .xlsx file. Defaults to NewAes/ELAT_DATA/llm_rubric_features.xlsx.",
    )
    parser.add_argument(
        "--features-file",
        help=(
            "Optional existing AES features workbook. When provided, LLM columns "
            "are merged into this workbook by essay_id and written to --output."
        ),
    )
    parser.add_argument("--text-column", help="Column containing essay text.")
    parser.add_argument("--essay-id-column", default="essay_id")
    parser.add_argument("--prompt-column", default="prompt_id")
    parser.add_argument("--model", default="llama3:8b")
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434/api/chat",
        help="Ollama chat API URL.",
    )
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay-seconds", type=float, default=10.0)
    parser.add_argument("--limit", type=int, help="Only process the first N essays.")
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument(
        "--save-every",
        type=int,
        default=25,
        help="Save partial output every N essays. Use 0 to save only at the end.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse existing LLM scores from the output workbook when present.",
    )
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def build_result_df(
    input_df: pd.DataFrame,
    llm_df: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    if args.features_file:
        features_path = Path(args.features_file)
        features_df = pd.read_excel(features_path)
        if args.essay_id_column not in features_df.columns:
            raise ValueError(
                f"Features file does not contain column: {args.essay_id_column}"
            )
        return features_df.drop(columns=LLM_TRAIT_COLUMNS, errors="ignore").merge(
            llm_df,
            on=args.essay_id_column,
            how="left",
            validate="one_to_one",
        )

    original_output = input_df.drop(columns=LLM_TRAIT_COLUMNS, errors="ignore")
    return original_output.merge(
        llm_df,
        on=args.essay_id_column,
        how="left",
        validate="one_to_one",
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if output_path.resolve() == input_path.resolve():
        raise ValueError("Output file must not overwrite the input file.")
    if args.features_file and output_path.resolve() == Path(args.features_file).resolve():
        raise ValueError("Output file must not overwrite the features file.")

    if input_path.suffix.lower() == ".csv":
        input_df = pd.read_csv(input_path)
    elif input_path.suffix.lower() == ".xlsx":
        input_df = pd.read_excel(input_path)
    else:
        raise ValueError("Input file must be .xlsx or .csv.")

    text_column = choose_column(
        list(input_df.columns),
        args.text_column,
        TEXT_COLUMN_CANDIDATES,
    )
    if args.essay_id_column not in input_df.columns:
        input_df[args.essay_id_column] = [
            f"essay_{index}" for index in range(1, len(input_df) + 1)
        ]

    rows_to_process = input_df.head(args.limit) if args.limit else input_df
    output_rows = []
    completed_ids = set()
    if args.resume and output_path.exists():
        existing_df = pd.read_excel(output_path)
        if args.essay_id_column in existing_df.columns:
            required_resume_columns = [args.essay_id_column, *LLM_TRAIT_COLUMNS]
            missing_resume_columns = [
                column
                for column in required_resume_columns
                if column not in existing_df.columns
            ]
            if missing_resume_columns:
                completed_mask = pd.Series(False, index=existing_df.index)
            else:
                completed_mask = existing_df[LLM_TRAIT_COLUMNS].notna().all(axis=1)
            completed_rows = existing_df.loc[
                completed_mask,
                [
                    column
                    for column in [args.essay_id_column, *LLM_TRAIT_COLUMNS]
                    if column in existing_df.columns
                ],
            ]
            output_rows = completed_rows.to_dict("records")
            completed_ids = set(completed_rows[args.essay_id_column].astype(str))
            if not args.quiet:
                print(f"Resuming with {len(completed_ids)} completed essays", flush=True)

    pending_rows = []
    for _, row in rows_to_process.iterrows():
        essay_id = normalize_cell(row.get(args.essay_id_column, ""))
        if str(essay_id) not in completed_ids:
            pending_rows.append(row)

    for index, row in enumerate(pending_rows, start=1):
        if not args.quiet:
            total_done = len(completed_ids) + index
            print(
                f"Scoring essay {total_done}/{len(rows_to_process)} "
                f"({index}/{len(pending_rows)} remaining run)",
                flush=True,
            )
        output_rows.append(evaluate_row(row, args, text_column, len(completed_ids) + index))
        if args.save_every and index % args.save_every == 0:
            partial_llm_df = pd.DataFrame(output_rows)
            partial_result_df = build_result_df(rows_to_process, partial_llm_df, args)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            partial_result_df.to_excel(output_path, index=False)
            if not args.quiet:
                print(f"Saved partial output after {index} essays", flush=True)
        if args.delay_seconds:
            time.sleep(args.delay_seconds)

    llm_df = pd.DataFrame(output_rows)
    result_df = build_result_df(rows_to_process, llm_df, args)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_excel(output_path, index=False)
    print(f"Saved {len(result_df)} rows to {output_path}")


if __name__ == "__main__":
    main()
