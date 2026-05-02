# Rule-Based AES Feature Extractor

This project provides a clean Python implementation of a rule-based Automated
Essay Scoring feature extractor. It extracts interpretable essay features and
computes a simple weighted score without using machine learning, LLMs, or any
web application framework.

## What It Does

The main entry point is:

```python
def extract_features(text: str) -> dict:
    ...
```

It returns lexical, syntactic, cohesion, and grammar-related features:

```python
{
    "word_count": ...,
    "sentence_count": ...,
    "mean_sentence_length": ...,
    "avg_word_freq": ...,
    "mtld": ...,
    "awl_ratio": ...,
    "clause_density": ...,
    "dependency_depth": ...,
    "noun_complexity": ...,
    "connective_density": ...,
    "lexical_overlap": ...,
    "grammar_errors_per_100": ...
}
```

The module also includes:

```python
def compute_score(features: dict) -> float:
    ...

def evaluate_essay(text: str) -> dict:
    ...
```

`evaluate_essay` returns both the score and the extracted feature dictionary.

## Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

Download the spaCy English model:

```bash
python -m spacy download en_core_web_sm
```

Download the NLTK sentence tokenizer data:

```bash
python -m nltk.downloader punkt punkt_tab
```

LanguageTool also requires Java. You can check that Java is available with:

```bash
java -version
```

## Usage

Run the included sample:

```bash
python aes_feature_extractor.py
```

Use it from another Python file:

```python
from aes_feature_extractor import evaluate_essay

essay = "Students benefit from attending class because lectures provide useful guidance."
result = evaluate_essay(essay)

print(result["score"])
print(result["features"])
```

## Feature Summary

`word_count`  
Counts alphabetic spaCy tokens only.

`sentence_count`  
Counts sentences using spaCy.

`mean_sentence_length`  
Computes words per sentence.

`avg_word_freq`  
Uses `wordfreq.zipf_frequency`. Lower values indicate less common vocabulary.

`mtld`  
Uses `lexical_diversity` to estimate lexical diversity. Very short essays return
a safe fallback.

`awl_ratio`  
Computes the ratio of essay words found in a placeholder Academic Word List set.

`clause_density`  
Approximates clause use by counting selected dependency labels:
`ccomp`, `xcomp`, and `advcl`.

`dependency_depth`  
Computes the average number of dependency hops from tokens to their sentence
root.

`noun_complexity`  
Computes the average number of syntactic children attached to noun tokens.

`connective_density`  
Counts selected single-word and multi-word connectives per 100 words.

`lexical_overlap`  
Computes average Jaccard overlap between adjacent sentence word sets.

`grammar_errors_per_100`  
Uses `language_tool_python` to estimate grammar matches per 100 words. If
LanguageTool fails, this feature returns `None`.

## Scoring

The scoring function is intentionally simple and transparent. It uses these
manual weights:

- `mtld`: 25%
- `awl_ratio`: 30%
- `avg_word_freq`: 20%, inverted because lower frequency suggests more advanced
  vocabulary
- `grammar_errors_per_100`: 25%, inverted because fewer errors is better

The final score is returned on a 0 to 100 scale.

## Notes

This is a rule-based feature extractor, not a trained scoring model. The score
is best understood as a transparent heuristic based on selected features, not as
a validated essay score.
