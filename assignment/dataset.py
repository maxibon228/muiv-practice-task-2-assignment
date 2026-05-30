"""Dataset loader for the practice assignment.

When imported, the module loads ``dataset.csv`` into the global variable ``df``.
When executed directly, it prints a small analytical report to the console and
writes the same text to ``report.txt`` using UTF-8 encoding.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import pandas as pd
from pandas.api.types import is_numeric_dtype

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.csv"
REPORT_PATH = BASE_DIR / "report.txt"

# The assignment checks that this global value is available after importing the
# module.  No output is produced during import.
df = pd.read_csv(DATASET_PATH)

# Columns that are numeric by storage type, but categorical by meaning for the
# datasets used in this practice.
CATEGORICAL_COLUMNS = {
    "class", "passenger_class", "класс_пассажира", "порт_загрузки", "выжил",
    "sex", "smoking", "death", "death_event", "deathevent",
    "anaemia", "anemia", "diabetes", "high_blood_pressure",
}

ID_COLUMNS = {"id", "index", "unnamed: 0"}


def normalize_column_name(name: str) -> str:
    """Return a normalized column name used for semantic checks."""
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


def is_id_column(column: str) -> bool:
    """Return True for technical index/id columns that should not be analysed."""
    normalized = normalize_column_name(column)
    return normalized in ID_COLUMNS or normalized.startswith("unnamed")


def is_categorical_column(column: str) -> bool:
    """Return True for columns interpreted as categorical values."""
    return normalize_column_name(column) in CATEGORICAL_COLUMNS


def numeric_value_columns(data: pd.DataFrame | None = None) -> list[str]:
    """Columns with countable numeric values, excluding IDs and categories."""
    source = df if data is None else data
    return [
        column
        for column in source.columns
        if is_numeric_dtype(source[column])
        and not is_id_column(column)
        and not is_categorical_column(column)
    ]


def categorical_value_columns(data: pd.DataFrame | None = None) -> list[str]:
    """Columns treated as categorical values in the report."""
    source = df if data is None else data
    return [column for column in source.columns if is_categorical_column(column)]


def dataframe_info_to_string(data: pd.DataFrame) -> str:
    """Return the standard pandas ``info`` output as a string."""
    buffer = io.StringIO()
    data.info(buf=buffer)
    return buffer.getvalue().rstrip()


def format_numeric_statistics(data: pd.DataFrame, columns: Iterable[str]) -> str:
    """Return mean, median and standard deviation for numeric columns."""
    lines = ["Колонка> среднее медиана отклонение"]
    for column in columns:
        values = data[column]
        lines.append(
            f"{column}> {values.mean():.2f}; {values.median():.2f}; {values.std():.2f}"
        )
    return "\n".join(lines)


def format_categorical_statistics(data: pd.DataFrame, columns: Iterable[str]) -> str:
    """Return frequency tables for categorical columns.

    The practice example shows the standard pandas representation of
    ``Series.value_counts()`` (including ``Name: count, dtype: int64``),
    so formatting is delegated to pandas instead of assembling a custom
    string manually.
    """
    blocks: list[str] = []
    for column in columns:
        blocks.append(str(data[column].value_counts(dropna=True)))
    return "\n".join(blocks)


def build_report(data: pd.DataFrame | None = None) -> str:
    """Build the report required for assignment 1."""
    source = df if data is None else data
    numeric_columns = numeric_value_columns(source)
    categorical_columns = categorical_value_columns(source)

    sections = [
        str(source.shape),
        dataframe_info_to_string(source),
        source.isna().sum().to_string(),
        format_numeric_statistics(source, numeric_columns),
    ]
    if categorical_columns:
        sections.append(format_categorical_statistics(source, categorical_columns))
    return "\n".join(sections)


def main() -> None:
    """Print the dataset report and duplicate it into ``report.txt``."""
    report = build_report(df)
    print(report)
    REPORT_PATH.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
