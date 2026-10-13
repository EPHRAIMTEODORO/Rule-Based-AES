"""Focused regression tests for pending HITL decisions and whole grades."""

from __future__ import annotations

import unittest

from HITL import app_backend, hitl_processor, hybrid_llm_aes


class HumanDecisionWorkflowTests(unittest.TestCase):
    def test_fresh_processed_row_is_pending(self) -> None:
        row = hitl_processor._with_initial_decision_fields(
            {"llm_recommended_score": 4},
            pending=True,
        )

        self.assertEqual(row["Decision_Status"], "Pending")
        self.assertEqual(row["Rater_Final_Score"], "")
        self.assertEqual(row["Rater_Final_Placement"], "")
        self.assertEqual(row["Rater_Action"], "")

    def test_model_recommendation_rounds_to_whole_grade(self) -> None:
        result = hybrid_llm_aes.normalize_llm_result(
            {"recommended_score": 4.5},
            "essay-1",
        )

        self.assertEqual(result["recommended_score"], 5)
        self.assertIsInstance(result["recommended_score"], int)

    def test_human_final_score_rejects_half_points(self) -> None:
        with self.assertRaisesRegex(ValueError, "whole number"):
            app_backend._normalize_final_score(3.5)

    def test_human_final_score_is_an_integer(self) -> None:
        self.assertEqual(app_backend._normalize_final_score("6"), 6)
        self.assertIsInstance(app_backend._normalize_final_score("6"), int)

    def test_default_model_timeout_is_ten_minutes(self) -> None:
        self.assertEqual(hybrid_llm_aes.DEFAULT_LLM_TIMEOUT_SECONDS, 600)
        self.assertEqual(
            hitl_processor.ProcessorOptions().timeout,
            hybrid_llm_aes.DEFAULT_LLM_TIMEOUT_SECONDS,
        )


if __name__ == "__main__":
    unittest.main()
