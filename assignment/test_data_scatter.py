from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from data_scatter import (
    build_scatter,
    create_scatter_figure,
    digital_root,
    display_label,
    get_numeric_columns,
    marker_for_student_id,
    timestamped_graph_name,
)


def test_digital_root_and_marker() -> None:
    assert digital_root(70193935) == 1
    assert marker_for_student_id(70193935) == "^"


def test_timestamped_graph_name() -> None:
    assert timestamped_graph_name(datetime(2026, 5, 29, 9, 5, 2)) == "graph09_05_02.png"




def test_display_label_returns_russian_labels() -> None:
    assert display_label("platelets") == "Тромбоциты"
    assert display_label("serum creatinine") == "Креатинин сыворотки"
    assert display_label("unknown") == "unknown"


def test_create_scatter_figure_uses_russian_axis_labels() -> None:
    data = pd.DataFrame({"platelets": [1, 2, 3], "serum creatinine": [4, 5, 6]})
    figure = create_scatter_figure(data, "platelets", "serum creatinine", "^")
    axis = figure.axes[0]
    assert axis.get_xlabel() == "Тромбоциты"
    assert axis.get_ylabel() == "Креатинин сыворотки"
    assert axis.get_title() == "Тромбоциты / Креатинин сыворотки"

def test_get_numeric_columns_excludes_categories_and_ids_but_keeps_missing_numeric() -> None:
    data = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "platelets": [120.0, 130.0, 140.0],
            "serum creatinine": [0.9, 1.1, 1.2],
            "hemoglobin": [None, 13.0, 14.0],
            "sex": [0, 1, 1],
            "smoking": [1, 0, 0],
            "death": [0, 1, 0],
        }
    )
    assert get_numeric_columns(data) == ["platelets", "serum creatinine", "hemoglobin"]


def test_build_scatter_creates_file(tmp_path: Path) -> None:
    data = pd.DataFrame({"A": [1, 2, 3, np.nan], "B": [4, 5, 6, 7]})
    output_file = tmp_path / "test_scatter.png"
    summary = build_scatter(data, x_col="A", y_col="B", marker="^", output_path=output_file)
    assert summary["n_points"] == 3
    assert summary["removed"] == 1
    assert output_file.exists()


def test_build_scatter_drops_only_incomplete_pairs(tmp_path: Path) -> None:
    data = pd.DataFrame({"A": [1, 2, None, 4], "B": [10, None, 30, 40]})
    output_file = tmp_path / "pairwise_dropna.png"
    summary = build_scatter(data, x_col="A", y_col="B", marker="^", output_path=output_file)
    assert summary["n_points"] == 2
    assert summary["removed"] == 2
    assert output_file.exists()


def test_build_scatter_allows_same_column(tmp_path: Path) -> None:
    data = pd.DataFrame({"A": [1, 2, 3, 4]})
    output_file = tmp_path / "same_column.png"
    summary = build_scatter(data, x_col="A", y_col="A", marker="^", output_path=output_file)
    assert summary["n_points"] == 4
    assert summary["correlation"] == 1.0
    assert output_file.exists()
