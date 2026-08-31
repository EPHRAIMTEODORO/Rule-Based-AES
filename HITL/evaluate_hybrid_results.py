"""Evaluate AES prediction columns against human rater scores."""

from __future__ import annotations

import argparse
import csv
import math
from typing import Optional


def to_float(value: object) -> Optional[float]:
    """Convert a CSV value to float when possible."""
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except ValueError:
        return None


def pearson(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation."""
    if len(xs) < 2:
        return float("nan")
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = sum((x - mean_x) ** 2 for x in xs)
    denom_y = sum((y - mean_y) ** 2 for y in ys)
    if denom_x == 0 or denom_y == 0:
        return float("nan")
    return numerator / math.sqrt(denom_x * denom_y)


def mean_absolute_error(predictions: list[float], targets: list[float]) -> float:
    """Compute mean absolute error."""
    return sum(abs(prediction - target) for prediction, target in zip(predictions, targets)) / len(targets)


def agreement_rate(
    predictions: list[float],
    targets: list[float],
    tolerance: float,
) -> float:
    """Compute agreement within a score tolerance."""
    matches = sum(
        1
        for prediction, target in zip(predictions, targets)
        if abs(prediction - target) <= tolerance
    )
    return matches / len(targets)


def round_to_half(value: float) -> float:
    """Round a score to the nearest half point."""
    return round(value * 2) / 2


def quadratic_weighted_kappa(
    predictions: list[float],
    targets: list[float],
    min_score: float,
    max_score: float,
    step: float,
) -> float:
    """Compute quadratic weighted kappa for half-point score bands."""
    labels = []
    current = min_score
    while current <= max_score + 1e-9:
        labels.append(round(current, 5))
        current += step

    label_to_index = {label: index for index, label in enumerate(labels)}
    size = len(labels)
    observed = [[0.0 for _ in labels] for _ in labels]
    predicted_counts = [0.0 for _ in labels]
    target_counts = [0.0 for _ in labels]

    for prediction, target in zip(predictions, targets):
        prediction_label = min(max(round_to_half(prediction), min_score), max_score)
        target_label = min(max(round_to_half(target), min_score), max_score)
        prediction_index = label_to_index[prediction_label]
        target_index = label_to_index[target_label]
        observed[prediction_index][target_index] += 1
        predicted_counts[prediction_index] += 1
        target_counts[target_index] += 1

    total = len(predictions)
    observed_weighted = 0.0
    expected_weighted = 0.0
    max_distance = (size - 1) ** 2

    for prediction_index in range(size):
        for target_index in range(size):
            weight = ((prediction_index - target_index) ** 2) / max_distance
            expected = predicted_counts[prediction_index] * target_counts[target_index] / total
            observed_weighted += weight * observed[prediction_index][target_index]
            expected_weighted += weight * expected

    if expected_weighted == 0:
        return float("nan")
    return 1 - (observed_weighted / expected_weighted)


def scale_prediction(value: float, scale: str) -> float:
    """Scale prediction columns into the human 1-6 score range."""
    if scale == "aes-0-100":
        return 1 + (value / 100) * 5
    return value


def evaluate_column(
    rows: list[dict],
    score_column: str,
    prediction_column: str,
    scale: str,
) -> dict:
    """Evaluate one prediction column against the human score."""
    targets = []
    predictions = []

    for row in rows:
        target = to_float(row.get(score_column))
        prediction = to_float(row.get(prediction_column))
        if target is None or prediction is None:
            continue
        targets.append(target)
        predictions.append(scale_prediction(prediction, scale))

    if not targets:
        raise ValueError(f"No usable rows for prediction column: {prediction_column}")

    return {
        "column": prediction_column,
        "n": len(targets),
        "pearson": pearson(predictions, targets),
        "mae": mean_absolute_error(predictions, targets),
        "exact_agreement": agreement_rate(predictions, targets, tolerance=0.25),
        "adjacent_agreement": agreement_rate(predictions, targets, tolerance=0.5),
        "qwk": quadratic_weighted_kappa(
            predictions,
            targets,
            min_score=1.0,
            max_score=6.0,
            step=0.5,
        ),
    }


def parse_prediction_arg(value: str) -> tuple[str, str]:
    """Parse prediction args like column or column:scale."""
    if ":" not in value:
        return value, "human-1-6"
    column, scale = value.split(":", 1)
    if scale not in {"human-1-6", "aes-0-100"}:
        raise argparse.ArgumentTypeError(
            "Scale must be one of: human-1-6, aes-0-100"
        )
    return column, scale


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate AES prediction columns against human scores."
    )
    parser.add_argument("--input", "-i", required=True, help="Hybrid result CSV.")
    parser.add_argument(
        "--score-column",
        default="score",
        help="Human score column. Defaults to score.",
    )
    parser.add_argument(
        "--prediction",
        action="append",
        type=parse_prediction_arg,
        required=True,
        help=(
            "Prediction column, optionally with scale. Examples: "
            "llm_recommended_score or aes_score:aes-0-100"
        ),
    )
    return parser.parse_args()


def main() -> None:
    """Run evaluation and print metric rows."""
    args = parse_args()
    with open(args.input, newline="", encoding="utf-8-sig") as input_file:
        rows = list(csv.DictReader(input_file))

    print("column,n,pearson,mae,exact_agreement,adjacent_agreement,qwk")
    for prediction_column, scale in args.prediction:
        metrics = evaluate_column(rows, args.score_column, prediction_column, scale)
        print(
            f"{metrics['column']},{metrics['n']},"
            f"{metrics['pearson']:.5f},{metrics['mae']:.5f},"
            f"{metrics['exact_agreement']:.5f},"
            f"{metrics['adjacent_agreement']:.5f},"
            f"{metrics['qwk']:.5f}"
        )


if __name__ == "__main__":
    main()
