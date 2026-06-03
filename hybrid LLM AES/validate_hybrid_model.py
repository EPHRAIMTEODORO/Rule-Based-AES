"""Validate rule-based, LLM, and hybrid AES predictions.

This script intentionally uses only the Python standard library so it can run
in small research environments without requiring scikit-learn.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from typing import Optional

from evaluate_hybrid_results import (
    mean_absolute_error,
    pearson,
    quadratic_weighted_kappa,
    scale_prediction,
    to_float,
)


DEFAULT_FEATURE_COLUMNS = [
    "aes_paragraph_count",
    "aes_word_count",
    "aes_sentence_count",
    "aes_mean_sentence_length",
    "aes_avg_word_freq",
    "aes_mtld",
    "aes_awl_ratio",
    "aes_clause_density",
    "aes_dependency_depth",
    "aes_noun_complexity",
    "aes_connective_density",
    "aes_lexical_overlap",
    "aes_grammar_errors_per_100",
    "llm_organization",
    "llm_paragraph_development",
    "llm_supporting_detail",
    "llm_abstract_elaboration",
    "llm_prompt_control",
    "llm_comprehensibility",
    "llm_grammar_meaning_impact",
]

AES_FEATURE_COLUMNS = [
    column for column in DEFAULT_FEATURE_COLUMNS if column.startswith("aes_")
]

LLM_TRAIT_COLUMNS = [
    column for column in DEFAULT_FEATURE_COLUMNS if column.startswith("llm_")
]


@dataclass
class Dataset:
    """Prepared dataset used by validation routines."""

    rows: list[dict]
    targets: list[float]
    groups: list[str]


@dataclass
class LinearModel:
    """A fitted standardized Ridge regression model."""

    columns: list[str]
    means: list[float]
    stds: list[float]
    coefficients: list[float]


def round_to_score_range(value: float) -> float:
    """Keep predictions inside the human score range."""
    return min(max(value, 1.0), 6.0)


def row_value(row: dict, column: str) -> Optional[float]:
    """Read a numeric row value, scaling known score columns when needed."""
    value = to_float(row.get(column))
    if value is None:
        return None
    if column == "aes_score":
        return scale_prediction(value, "aes-0-100")
    return value


def load_dataset(
    path: str,
    score_column: str,
    group_column: Optional[str],
) -> Dataset:
    """Load rows with usable human scores."""
    with open(path, newline="", encoding="utf-8-sig") as input_file:
        rows = list(csv.DictReader(input_file))

    kept_rows = []
    targets = []
    groups = []
    for index, row in enumerate(rows):
        target = to_float(row.get(score_column))
        if target is None:
            continue
        kept_rows.append(row)
        targets.append(target)
        if group_column:
            groups.append(str(row.get(group_column, "")).strip() or f"row-{index}")
        else:
            groups.append(f"row-{index}")

    if not kept_rows:
        raise ValueError(f"No usable rows with score column: {score_column}")

    return Dataset(rows=kept_rows, targets=targets, groups=groups)


def usable_columns(rows: list[dict], requested_columns: list[str]) -> list[str]:
    """Keep columns that have at least one numeric value."""
    columns = []
    for column in requested_columns:
        if any(row_value(row, column) is not None for row in rows):
            columns.append(column)
    return columns


def column_mean(rows: list[dict], column: str, indexes: list[int]) -> float:
    """Compute a training-set mean for imputation."""
    values = [
        row_value(rows[index], column)
        for index in indexes
        if row_value(rows[index], column) is not None
    ]
    if not values:
        return 0.0
    return sum(values) / len(values)


def feature_matrix(
    rows: list[dict],
    columns: list[str],
    indexes: list[int],
    imputers: Optional[dict[str, float]] = None,
) -> tuple[list[list[float]], dict[str, float]]:
    """Build a numeric feature matrix with mean imputation."""
    if imputers is None:
        imputers = {column: column_mean(rows, column, indexes) for column in columns}

    matrix = []
    for index in indexes:
        row = rows[index]
        matrix.append(
            [
                row_value(row, column)
                if row_value(row, column) is not None
                else imputers[column]
                for column in columns
            ]
        )
    return matrix, imputers


def standardize_train(matrix: list[list[float]]) -> tuple[list[list[float]], list[float], list[float]]:
    """Standardize training features and return means/stds."""
    if not matrix:
        return [], [], []
    width = len(matrix[0])
    means = [sum(row[i] for row in matrix) / len(matrix) for i in range(width)]
    stds = []
    for i in range(width):
        variance = sum((row[i] - means[i]) ** 2 for row in matrix) / len(matrix)
        stds.append(math.sqrt(variance) or 1.0)
    standardized = [
        [(row[i] - means[i]) / stds[i] for i in range(width)]
        for row in matrix
    ]
    return standardized, means, stds


def standardize_apply(
    matrix: list[list[float]],
    means: list[float],
    stds: list[float],
) -> list[list[float]]:
    """Apply training standardization to new rows."""
    return [
        [(row[i] - means[i]) / stds[i] for i in range(len(row))]
        for row in matrix
    ]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a dense linear system with Gaussian elimination."""
    size = len(vector)
    augmented = [matrix[i][:] + [vector[i]] for i in range(size)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) < 1e-12:
            augmented[pivot][col] = 1e-12
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]

        pivot_value = augmented[col][col]
        augmented[col] = [value / pivot_value for value in augmented[col]]

        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            augmented[row] = [
                augmented[row][i] - factor * augmented[col][i]
                for i in range(size + 1)
            ]

    return [augmented[i][-1] for i in range(size)]


def fit_ridge(
    rows: list[dict],
    targets: list[float],
    columns: list[str],
    train_indexes: list[int],
    alpha: float,
) -> tuple[LinearModel, dict[str, float]]:
    """Fit standardized Ridge regression with an unregularized intercept."""
    raw_x, imputers = feature_matrix(rows, columns, train_indexes)
    x, means, stds = standardize_train(raw_x)
    y = [targets[index] for index in train_indexes]

    design = [[1.0] + row for row in x]
    width = len(design[0])
    xtx = [[0.0 for _ in range(width)] for _ in range(width)]
    xty = [0.0 for _ in range(width)]

    for row, target in zip(design, y):
        for i in range(width):
            xty[i] += row[i] * target
            for j in range(width):
                xtx[i][j] += row[i] * row[j]

    for i in range(1, width):
        xtx[i][i] += alpha

    coefficients = solve_linear_system(xtx, xty)
    return LinearModel(columns, means, stds, coefficients), imputers


def predict_ridge(
    model: LinearModel,
    rows: list[dict],
    indexes: list[int],
    imputers: dict[str, float],
) -> list[float]:
    """Predict with a fitted Ridge model."""
    raw_x, _ = feature_matrix(rows, model.columns, indexes, imputers)
    x = standardize_apply(raw_x, model.means, model.stds)
    predictions = []
    for row in x:
        value = model.coefficients[0]
        for coefficient, feature in zip(model.coefficients[1:], row):
            value += coefficient * feature
        predictions.append(round_to_score_range(value))
    return predictions


def direct_predictions(
    rows: list[dict],
    indexes: list[int],
    column: str,
) -> tuple[list[float], list[int]]:
    """Read direct predictions and return indexes where they are present."""
    predictions = []
    kept_indexes = []
    for index in indexes:
        value = row_value(rows[index], column)
        if value is not None:
            predictions.append(round_to_score_range(value))
            kept_indexes.append(index)
    return predictions, kept_indexes


def metric_row(name: str, predictions: list[float], targets: list[float]) -> dict:
    """Compute validation metrics for predictions on the human 1-6 scale."""
    return {
        "model": name,
        "n": len(targets),
        "pearson": pearson(predictions, targets),
        "mae": mean_absolute_error(predictions, targets),
        "qwk": quadratic_weighted_kappa(
            predictions,
            targets,
            min_score=1.0,
            max_score=6.0,
            step=0.5,
        ),
    }


def shuffled_indexes(size: int, seed: int) -> list[int]:
    """Return shuffled row indexes."""
    indexes = list(range(size))
    random.Random(seed).shuffle(indexes)
    return indexes


def split_indexes(
    groups: list[str],
    test_size: float,
    seed: int,
    grouped: bool,
) -> tuple[list[int], list[int]]:
    """Create a deterministic train/test split."""
    if not grouped:
        indexes = shuffled_indexes(len(groups), seed)
        test_count = max(1, round(len(indexes) * test_size))
        return indexes[test_count:], indexes[:test_count]

    unique_groups = sorted(set(groups))
    random.Random(seed).shuffle(unique_groups)
    target_test_count = max(1, round(len(groups) * test_size))
    test_groups = set()
    test_count = 0
    for group in unique_groups:
        test_groups.add(group)
        test_count += groups.count(group)
        if test_count >= target_test_count:
            break
    train_indexes = [i for i, group in enumerate(groups) if group not in test_groups]
    test_indexes = [i for i, group in enumerate(groups) if group in test_groups]
    return train_indexes, test_indexes


def kfold_indexes(
    groups: list[str],
    folds: int,
    seed: int,
    grouped: bool,
) -> list[list[int]]:
    """Create deterministic k-fold validation indexes."""
    if not grouped:
        indexes = shuffled_indexes(len(groups), seed)
        return [indexes[i::folds] for i in range(folds)]

    unique_groups = sorted(set(groups))
    random.Random(seed).shuffle(unique_groups)
    fold_groups = [set() for _ in range(folds)]
    fold_sizes = [0 for _ in range(folds)]
    for group in unique_groups:
        smallest_fold = min(range(folds), key=lambda i: fold_sizes[i])
        fold_groups[smallest_fold].add(group)
        fold_sizes[smallest_fold] += groups.count(group)
    return [
        [i for i, group in enumerate(groups) if group in group_set]
        for group_set in fold_groups
    ]


def evaluate_direct(
    dataset: Dataset,
    name: str,
    column: str,
    test_indexes: list[int],
) -> dict:
    """Evaluate a direct prediction column on selected rows."""
    predictions, kept_indexes = direct_predictions(dataset.rows, test_indexes, column)
    targets = [dataset.targets[index] for index in kept_indexes]
    return metric_row(name, predictions, targets)


def evaluate_ridge(
    dataset: Dataset,
    name: str,
    columns: list[str],
    train_indexes: list[int],
    test_indexes: list[int],
    alpha: float,
) -> dict:
    """Fit Ridge on train indexes and evaluate on test indexes."""
    model, imputers = fit_ridge(
        dataset.rows,
        dataset.targets,
        columns,
        train_indexes,
        alpha,
    )
    predictions = predict_ridge(model, dataset.rows, test_indexes, imputers)
    targets = [dataset.targets[index] for index in test_indexes]
    return metric_row(name, predictions, targets)


def aggregate_metrics(rows: list[dict], model: str) -> dict:
    """Average repeated fold metric rows."""
    model_rows = [row for row in rows if row["model"] == model]
    output = {"model": model, "n": sum(row["n"] for row in model_rows)}
    for metric in ["pearson", "mae", "qwk"]:
        values = [row[metric] for row in model_rows if not math.isnan(row[metric])]
        output[metric] = sum(values) / len(values) if values else float("nan")
    return output


def format_metric(value: float) -> str:
    """Format metrics consistently."""
    if math.isnan(value):
        return "nan"
    return f"{value:.5f}"


def print_rows(title: str, rows: list[dict]) -> None:
    """Print metric rows as CSV text."""
    print(title)
    print("model,n,pearson,mae,qwk")
    for row in rows:
        print(
            f"{row['model']},{row['n']},"
            f"{format_metric(row['pearson'])},"
            f"{format_metric(row['mae'])},"
            f"{format_metric(row['qwk'])}"
        )
    print()


def score_distribution(targets: list[float]) -> list[tuple[float, int]]:
    """Return score counts."""
    counts: dict[float, int] = {}
    for target in targets:
        counts[target] = counts.get(target, 0) + 1
    return sorted(counts.items())


def prompt_distribution(rows: list[dict], prompt_column: str) -> list[tuple[str, int]]:
    """Return prompt counts."""
    counts: dict[str, int] = {}
    for row in rows:
        prompt = str(row.get(prompt_column, "")).strip() or "(blank)"
        counts[prompt] = counts.get(prompt, 0) + 1
    return sorted(counts.items())


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Validate rule-based, LLM, and hybrid AES predictions."
    )
    parser.add_argument("--input", "-i", required=True, help="Hybrid result CSV.")
    parser.add_argument(
        "--score-column",
        default="score",
        help="Human score column. Defaults to score.",
    )
    parser.add_argument(
        "--prompt-column",
        default="prompt_id",
        help="Prompt column used for reporting. Defaults to prompt_id.",
    )
    parser.add_argument(
        "--group-column",
        default=None,
        help="Optional group column for grouped train/test and CV splits.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.25,
        help="Held-out test fraction. Defaults to 0.25.",
    )
    parser.add_argument(
        "--folds",
        type=int,
        default=5,
        help="Number of CV folds. Defaults to 5.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=20,
        help="Number of repeated CV shuffles. Defaults to 20.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed. Defaults to 42.",
    )
    parser.add_argument(
        "--ridge-alpha",
        type=float,
        default=10.0,
        help="Ridge regularization strength. Defaults to 10.0.",
    )
    return parser.parse_args()


def main() -> None:
    """Run validation."""
    args = parse_args()
    grouped = args.group_column is not None
    dataset = load_dataset(args.input, args.score_column, args.group_column)
    all_indexes = list(range(len(dataset.rows)))

    feature_columns = usable_columns(dataset.rows, DEFAULT_FEATURE_COLUMNS)
    aes_feature_columns = usable_columns(dataset.rows, AES_FEATURE_COLUMNS)
    llm_trait_columns = usable_columns(dataset.rows, LLM_TRAIT_COLUMNS)
    aes_plus_llm_score_columns = usable_columns(
        dataset.rows,
        AES_FEATURE_COLUMNS + ["llm_recommended_score"],
    )

    print(f"rows,{len(dataset.rows)}")
    print(f"score_column,{args.score_column}")
    print(f"group_column,{args.group_column or ''}")
    print("score_distribution," + "; ".join(
        f"{score:g}:{count}" for score, count in score_distribution(dataset.targets)
    ))
    if args.prompt_column:
        print("prompt_distribution," + "; ".join(
            f"{prompt}:{count}"
            for prompt, count in prompt_distribution(dataset.rows, args.prompt_column)
        ))
    print()

    full_rows = [
        evaluate_direct(dataset, "aes_score_scaled", "aes_score", all_indexes),
        evaluate_direct(dataset, "llm_recommended_score", "llm_recommended_score", all_indexes),
    ]
    print_rows("full_sample_metrics", full_rows)

    train_indexes, test_indexes = split_indexes(
        dataset.groups,
        args.test_size,
        args.seed,
        grouped,
    )
    holdout_rows = [
        evaluate_direct(dataset, "aes_score_scaled", "aes_score", test_indexes),
        evaluate_direct(dataset, "llm_recommended_score", "llm_recommended_score", test_indexes),
    ]
    if aes_feature_columns:
        holdout_rows.append(
            evaluate_ridge(
                dataset,
                "ridge_aes_features",
                aes_feature_columns,
                train_indexes,
                test_indexes,
                args.ridge_alpha,
            )
        )
    if llm_trait_columns:
        holdout_rows.append(
            evaluate_ridge(
                dataset,
                "ridge_llm_traits",
                llm_trait_columns,
                train_indexes,
                test_indexes,
                args.ridge_alpha,
            )
        )
    if aes_plus_llm_score_columns:
        holdout_rows.append(
            evaluate_ridge(
                dataset,
                "ridge_aes_plus_llm_score",
                aes_plus_llm_score_columns,
                train_indexes,
                test_indexes,
                args.ridge_alpha,
            )
        )
    if feature_columns:
        holdout_rows.append(
            evaluate_ridge(
                dataset,
                "ridge_hybrid_features",
                feature_columns,
                train_indexes,
                test_indexes,
                args.ridge_alpha,
            )
        )
    print_rows("holdout_metrics", holdout_rows)

    repeated_rows = []
    for repeat in range(args.repeats):
        folds = kfold_indexes(dataset.groups, args.folds, args.seed + repeat, grouped)
        repeat_predictions: dict[str, list[float]] = {}
        repeat_targets: dict[str, list[float]] = {}

        def add_predictions(
            model_name: str,
            predictions: list[float],
            target_values: list[float],
        ) -> None:
            repeat_predictions.setdefault(model_name, []).extend(predictions)
            repeat_targets.setdefault(model_name, []).extend(target_values)

        for fold_index, test_fold in enumerate(folds):
            if not test_fold:
                continue
            train_fold = [
                index
                for index in range(len(dataset.rows))
                if index not in set(test_fold)
            ]
            predictions, kept_indexes = direct_predictions(
                dataset.rows,
                test_fold,
                "aes_score",
            )
            add_predictions(
                "aes_score_scaled",
                predictions,
                [dataset.targets[index] for index in kept_indexes],
            )

            predictions, kept_indexes = direct_predictions(
                dataset.rows,
                test_fold,
                "llm_recommended_score",
            )
            add_predictions(
                "llm_recommended_score",
                predictions,
                [dataset.targets[index] for index in kept_indexes],
            )

            if aes_feature_columns:
                model, imputers = fit_ridge(
                    dataset.rows,
                    dataset.targets,
                    aes_feature_columns,
                    train_fold,
                    args.ridge_alpha,
                )
                predictions = predict_ridge(
                    model,
                    dataset.rows,
                    test_fold,
                    imputers,
                )
                add_predictions(
                    "ridge_aes_features",
                    predictions,
                    [dataset.targets[index] for index in test_fold],
                )
            if llm_trait_columns:
                model, imputers = fit_ridge(
                    dataset.rows,
                    dataset.targets,
                    llm_trait_columns,
                    train_fold,
                    args.ridge_alpha,
                )
                predictions = predict_ridge(
                    model,
                    dataset.rows,
                    test_fold,
                    imputers,
                )
                add_predictions(
                    "ridge_llm_traits",
                    predictions,
                    [dataset.targets[index] for index in test_fold],
                )
            if aes_plus_llm_score_columns:
                model, imputers = fit_ridge(
                    dataset.rows,
                    dataset.targets,
                    aes_plus_llm_score_columns,
                    train_fold,
                    args.ridge_alpha,
                )
                predictions = predict_ridge(
                    model,
                    dataset.rows,
                    test_fold,
                    imputers,
                )
                add_predictions(
                    "ridge_aes_plus_llm_score",
                    predictions,
                    [dataset.targets[index] for index in test_fold],
                )
            if feature_columns:
                model, imputers = fit_ridge(
                    dataset.rows,
                    dataset.targets,
                    feature_columns,
                    train_fold,
                    args.ridge_alpha,
                )
                predictions = predict_ridge(
                    model,
                    dataset.rows,
                    test_fold,
                    imputers,
                )
                add_predictions(
                    "ridge_hybrid_features",
                    predictions,
                    [dataset.targets[index] for index in test_fold],
                )

        for model_name, predictions in repeat_predictions.items():
            repeated_rows.append(
                metric_row(model_name, predictions, repeat_targets[model_name])
            )

    model_names = []
    for row in repeated_rows:
        if row["model"] not in model_names:
            model_names.append(row["model"])
    cv_rows = [aggregate_metrics(repeated_rows, model) for model in model_names]
    print_rows(f"repeated_{args.folds}_fold_cv_metrics", cv_rows)


if __name__ == "__main__":
    main()
