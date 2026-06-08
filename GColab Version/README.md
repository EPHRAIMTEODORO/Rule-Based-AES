# Google Colab Version

This folder contains a Colab-ready copy of the current AES workflow. It does
not overwrite the original `NewAes` files.

## Files

- `Run_AES_Colab.ipynb`: step-by-step Colab notebook.
- `colab_add_grammar_features_to_full_sample.py`: adds LanguageTool grammar
  columns to the AES feature workbook.
- `colab_llm_rubric_features.py`: runs the anchored/improved Llama 3 rubric
  features with resume support.
- `requirements_colab.txt`: Python packages needed in Colab.

## Expected Inputs

The notebook assumes these files are available after cloning the repo:

- `NewAes/ELAT_DATA/essays.xlsx`
- `NewAes/ELAT_DATA/full_sample_aes_features.xlsx`

If you already have:

- `NewAes/ELAT_DATA/full_sample_aes_features_with_grammar.xlsx`

you can skip the grammar step and run only the LLM step.

## Main Output

The improved anchored LLM run writes:

```text
NewAes/ELAT_DATA/full_sample_aes_features_with_grammar_llm_improved_colab.xlsx
```

This is intentionally a new file so the original local output is not
overwritten.

## Resume Command

If Colab disconnects, rerun the setup cells, then rerun:

```bash
python "GColab Version/colab_llm_rubric_features.py" \
  --features-file "NewAes/ELAT_DATA/full_sample_aes_features_with_grammar.xlsx" \
  --output "NewAes/ELAT_DATA/full_sample_aes_features_with_grammar_llm_improved_colab.xlsx" \
  --resume \
  --timeout 240 \
  --retries 2 \
  --retry-delay-seconds 10 \
  --save-every 1 \
  --delay-seconds 1
```

The script will reuse completed rows in the output workbook and continue from
the missing essays.
