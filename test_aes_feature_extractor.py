import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aes_feature_extractor as extractor


class LanguageToolAndScoreTests(unittest.TestCase):
    def grammar_output(self, stdout, returncode=0):
        result = subprocess.CompletedProcess(["java"], returncode, stdout, None)
        with patch.object(extractor, "_language_tool_home", return_value=Path.cwd()), patch.object(
            extractor.subprocess, "run", return_value=result
        ):
            return extractor._check_grammar_with_cli("She go to school.")

    def test_missing_or_malformed_cli_output_is_unavailable(self):
        for output in (None, b"{}", "", "not json", "{bad}", '{"matches": null}',
                       '{"matches": [null]}', '{"matches": [{"rule": null}]}'):
            with self.subTest(output=output):
                self.assertIsNone(self.grammar_output(output))

    def test_failed_cli_is_not_treated_as_clean_grammar(self):
        self.assertIsNone(self.grammar_output('{"matches": []}', returncode=1))
        self.assertIsNone(self.grammar_output(None, returncode=1))

    def test_valid_cli_output_accepts_banner_and_clean_result(self):
        self.assertEqual(self.grammar_output('Starting Java\n{"matches": []}'), [])
        self.assertEqual(self.grammar_output('{"matches": [{"rule": {"id": "TEST"}}]}'), ["TEST"])

    def test_cli_failure_uses_existing_grammar_fallback(self):
        with patch.object(extractor, "_check_grammar_with_cli", return_value=None), patch.object(
            extractor, "_check_grammar_with_timeout", return_value=["TEST"]
        ):
            self.assertEqual(extractor._grammar_errors_per_100("She go to school.", 4), 25)

    def test_both_grammar_methods_failing_leave_metric_unavailable(self):
        with patch.object(extractor, "_check_grammar_with_cli", return_value=None), patch.object(
            extractor, "_check_grammar_with_timeout", return_value=None
        ):
            with self.assertLogs("aes_feature_extractor", level="WARNING"):
                self.assertIsNone(extractor._grammar_errors_per_100("She go to school.", 4))

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
