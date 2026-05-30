from pathlib import Path
import tkinter as tk

import pytest

import data_scatter
import dataset


def _create_root_or_skip() -> tk.Tk:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tkinter display is not available: {exc}")
    root.withdraw()
    return root


def test_gui_buttons_update_axes_and_save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _create_root_or_skip()

    monkeypatch.setattr(data_scatter, "BASE_DIR", tmp_path)
    monkeypatch.setattr(data_scatter.messagebox, "showinfo", lambda *args, **kwargs: None)

    app = data_scatter.ScatterApplication(
        root,
        dataset.df,
        data_scatter.get_numeric_columns(dataset.df),
    )

    assert app.x_col == "platelets"
    assert app.y_col == "serum creatinine"
    assert list(app.x_buttons) == list(app.y_buttons)
    assert app.root.title() == data_scatter.WINDOW_TITLE
    assert app.x_buttons["platelets"].cget("text") == "Тромбоциты"
    assert app.y_buttons["serum creatinine"].cget("text") == "Креатинин сыворотки"

    app.x_buttons["ejection fraction"].invoke()
    app.y_buttons["platelets"].invoke()
    root.update_idletasks()

    assert app.x_col == "ejection fraction"
    assert app.y_col == "platelets"
    assert app.figure is not None

    axis = app.figure.axes[0]
    assert axis.get_xlabel() == "Фракция выброса"
    assert axis.get_ylabel() == "Тромбоциты"

    output_path = app.save_current_graph()
    assert output_path.exists()
    assert output_path.name.startswith("graph")
    assert output_path.suffix == ".png"

    app.x_buttons["serum sodium"].invoke()
    app.y_buttons["serum sodium"].invoke()
    root.update_idletasks()

    assert app.x_col == "serum sodium"
    assert app.y_col == "serum sodium"

    root.destroy()
