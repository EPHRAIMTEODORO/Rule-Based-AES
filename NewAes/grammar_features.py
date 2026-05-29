import pandas as pd
import re
import language_tool_python
import argparse

# =========================
# LOAD DATA
# =========================
parser = argparse.ArgumentParser(description="Extract grammar features from an essay workbook.")
parser.add_argument("input_file", nargs="?", default="Language Features Sample.xlsx")
parser.add_argument("output_file", nargs="?", default="grammar_features_output.csv")
args = parser.parse_args()

INPUT_FILE = args.input_file
OUTPUT_FILE = args.output_file

df = pd.read_excel(INPUT_FILE)

# adjust this if your column name differs
TEXT_COLUMN = "text_clean"

# =========================
# INITIALIZE LANGUAGETOOL
# =========================
tool = language_tool_python.LanguageTool("en-US")

# =========================
# TOKENIZER
# =========================
def tokenize(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", str(text).lower())


# =========================
# FEATURE EXTRACTION
# =========================
grammar_errors = []
grammar_errors_per_100 = []

for text in df[TEXT_COLUMN].astype(str):
    tokens = tokenize(text)
    word_count = len(tokens)

    try:
        matches = tool.check(text)
        error_count = len(matches)
    except Exception as e:
        print("Error processing essay:", e)
        error_count = None

    grammar_errors.append(error_count)

    if word_count > 0 and error_count is not None:
        grammar_errors_per_100.append((error_count / word_count) * 100)
    else:
        grammar_errors_per_100.append(None)

# =========================
# SAVE RESULTS
# =========================
df["grammar_errors"] = grammar_errors
df["grammar_errors_per_100"] = grammar_errors_per_100

df.to_csv(OUTPUT_FILE, index=False)

print("Done.")
print(df[[
    "essay_id",
    "grammar_errors",
    "grammar_errors_per_100",
]].head())
