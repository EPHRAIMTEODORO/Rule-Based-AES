import argparse
import os
import re
from pathlib import Path

import language_tool_python
import pandas as pd


def tokenize(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", str(text).lower())


def main():
    parser = argparse.ArgumentParser(
        description="Add LanguageTool grammar features to an AES features workbook."
    )
    parser.add_argument(
        "--essays-file",
        default="NewAes/ELAT_DATA/essays.xlsx",
        help="Workbook containing essay_id and essay text.",
    )
    parser.add_argument(
        "--features-file",
        default="NewAes/ELAT_DATA/full_sample_aes_features.xlsx",
        help="Workbook to copy and enrich with grammar columns.",
    )
    parser.add_argument(
        "--output-file",
        default="NewAes/ELAT_DATA/full_sample_aes_features_with_grammar.xlsx",
        help="New workbook path. Existing source files are never overwritten.",
    )
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--id-column", default="essay_id")
    parser.add_argument(
        "--language-tool-version",
        default=os.environ.get("LANGUAGE_TOOL_VERSION", "5.9"),
        help="LanguageTool server version to use. Version 5.9 works with Java 8.",
    )
    args = parser.parse_args()

    essays_path = Path(args.essays_file)
    features_path = Path(args.features_file)
    output_path = Path(args.output_file)

    if output_path.resolve() in {essays_path.resolve(), features_path.resolve()}:
        raise ValueError("Output file must not overwrite an input workbook.")

    essays_df = pd.read_excel(essays_path)
    features_df = pd.read_excel(features_path)

    for column, path in [
        (args.id_column, essays_path),
        (args.text_column, essays_path),
        (args.id_column, features_path),
    ]:
        if column not in (
            essays_df.columns if path == essays_path else features_df.columns
        ):
            raise ValueError(f"Missing column {column!r} in {path}")

    if os.environ.get("JAVA_HOME"):
        os.environ["PATH"] = (
            str(Path(os.environ["JAVA_HOME"]) / "bin")
            + os.pathsep
            + os.environ.get("PATH", "")
        )

    tool = language_tool_python.LanguageTool(
        "en-US", language_tool_download_version=args.language_tool_version
    )

    grammar_rows = []
    for index, row in essays_df.iterrows():
        essay_id = row[args.id_column]
        text = "" if pd.isna(row[args.text_column]) else str(row[args.text_column])
        word_count = len(tokenize(text))

        try:
            error_count = len(tool.check(text))
        except Exception as exc:
            print(f"Error processing essay {essay_id}: {exc}")
            error_count = None

        grammar_rows.append(
            {
                args.id_column: essay_id,
                "grammar_errors": error_count,
                "grammar_errors_per_100": (
                    (error_count / word_count) * 100
                    if word_count > 0 and error_count is not None
                    else None
                ),
            }
        )

        if (index + 1) % 25 == 0:
            print(f"Processed {index + 1}/{len(essays_df)} essays")

    grammar_df = pd.DataFrame(grammar_rows)

    if grammar_df[args.id_column].duplicated().any():
        raise ValueError("Duplicate essay_id values found in grammar output.")

    enriched_df = features_df.drop(
        columns=["grammar_errors", "grammar_errors_per_100"], errors="ignore"
    ).merge(grammar_df, on=args.id_column, how="left", validate="one_to_one")

    missing = enriched_df["grammar_errors"].isna().sum()
    if missing:
        print(f"Warning: {missing} rows did not receive grammar features.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    enriched_df.to_excel(output_path, index=False)
    print(f"Saved {len(enriched_df)} rows to {output_path}")


if __name__ == "__main__":
    main()
