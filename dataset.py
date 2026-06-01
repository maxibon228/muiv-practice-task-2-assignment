"""
dataset.py — задание 1 практики.

При импорте загружает dataset.csv в глобальную переменную df.
При прямом запуске печатает отчёт в консоль и дублирует его в report.txt.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pandas as pd

DATASET_PATH = Path(__file__).resolve().with_name("dataset.csv")
df = pd.read_csv(DATASET_PATH)


def _normalize(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(name).strip().lower())


def _is_technical(name: str) -> bool:
    normalized = _normalize(name)
    return normalized in {"id", "index", "номер"} or normalized.startswith("unnamed")


def _is_category(name: str, series: pd.Series) -> bool:
    normalized = _normalize(name)
    if _is_technical(name):
        return False
    if any(hint in normalized for hint in [
        "sex", "gender", "smoking", "death", "survived", "class", "pclass", "embarked",
        "пол", "выжил", "класс", "порт", "категор",
    ]):
        return True
    if not pd.api.types.is_numeric_dtype(series):
        return True
    if any(hint in normalized for hint in ["количество", "сколько", "count", "number", "взросл", "дет"]):
        return False
    if any(hint in normalized for hint in ["serum", "platelet", "creatinine", "sodium", "fraction", "age", "возраст"]):
        return False
    numeric = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    return 0 < numeric.nunique() <= 5 and bool((numeric % 1 == 0).all())


def numeric_columns() -> list[str]:
    result: list[str] = []
    for column in df.columns:
        if _is_technical(str(column)):
            continue
        if pd.api.types.is_numeric_dtype(df[column]) and not _is_category(str(column), df[column]):
            result.append(str(column))
    return result


def categorical_columns() -> list[str]:
    result: list[str] = []
    for column in df.columns:
        if _is_category(str(column), df[column]):
            result.append(str(column))
    return result


def build_report() -> str:
    parts: list[str] = []
    parts.append(str(df.shape))

    buffer = io.StringIO()
    df.info(buf=buffer)
    parts.append(buffer.getvalue().rstrip())

    parts.append(str(df.isna().sum()))

    nums = numeric_columns()
    parts.append("Колонка>\tсреднее\tмедиана\tотклонение")
    for column in nums:
        series = pd.to_numeric(df[column], errors="coerce")
        parts.append(
            f"{column}>\t{series.mean():.2f};\t{series.median():.2f};\t{series.std():.2f}"
        )

    for column in categorical_columns():
        parts.append(str(column))
        parts.append(str(df[column].value_counts(dropna=True)))

    return "\n".join(parts) + "\n"


def main() -> None:
    report = build_report()
    print(report, end="")
    Path(__file__).resolve().with_name("report.txt").write_text(report, encoding="utf-8")


if __name__ == "__main__":
    main()
