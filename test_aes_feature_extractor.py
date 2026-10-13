import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aes_feature_extractor as extractor


class LanguageToolAndScoreTests(unittest.TestCase):
    def test_finds_versioned_language_tool_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            versioned_directory = root / "LanguageTool-6.8-SNAPSHOT"
            versioned_directory.mkdir()
            (versioned_directory / "languagetool-commandline.jar").touch()

            with patch.dict(os.environ, {"LTP_PATH": str(root)}):
                self.assertEqual(
                    extractor._language_tool_home(), versioned_directory
                )

    def test_missing_grammar_metric_is_not_treated_as_zero(self):
        features = {
            "mtld": 50,
            "awl_ratio": 0.1,
            "avg_word_freq": 4,
            "grammar_errors_per_100": None,
        }

        self.assertEqual(extractor.compute_score(features), 45.83333)

    def test_zero_grammar_errors_receives_full_grammar_credit(self):
        features = {
            "mtld": 50,
            "awl_ratio": 0.1,
            "avg_word_freq": 4,
            "grammar_errors_per_100": 0,
        }

        self.assertEqual(extractor.compute_score(features), 59.375)

    def test_score_is_unavailable_when_all_components_are_missing(self):
        self.assertIsNone(
            extractor.compute_score(
                {
                    "mtld": None,
                    "awl_ratio": None,
                    "avg_word_freq": None,
                    "grammar_errors_per_100": None,
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
