"""Задание №2: первичная визуализация данных.

Скрипт импортирует модуль dataset и использует глобальную переменную dataset.df.
При прямом запуске открывает Tkinter-приложение, где можно выбрать две числовые
колонки датасета и построить точечную диаграмму.

График отображается в tkinter.Canvas и сохраняется кнопкой в файл:
graphHH_MM_SS.png
"""

from __future__ import annotations

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Iterable

import matplotlib

# По условию график создаётся matplotlib, затем вставляется картинкой в Canvas.
matplotlib.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pandas as pd
from pandas.api.types import is_numeric_dtype
import tkinter as tk
from tkinter import messagebox

import dataset


BASE_DIR = Path(__file__).resolve().parent
STUDENT_ID = 70193935


WINDOW_TITLE = "Задание № 2: Разработка системы первичной визуализации данных"
SAVE_BUTTON_TEXT = "Сохранить"
MESSAGEBOX_TITLE = "Сохранение"

# Внутренние имена колонок в dataset.csv остаются исходными,
# а пользователю показываются русские подписи, как в русскоязычной методичке.
COLUMN_LABELS_RU = {
    "platelets": "Тромбоциты",
    "serum creatinine": "Креатинин сыворотки",
    "serum sodium": "Натрий сыворотки",
    "creatinine phosphokinase": "Креатинфосфокиназа",
    "ejection fraction": "Фракция выброса",
}


def display_label(column: str) -> str:
    """Возвращает русскую подпись колонки для интерфейса."""
    return COLUMN_LABELS_RU.get(column, column)


# Таблица стилей из задания №2:
# 1 — треугольник вверх, 2 — вправо, 3 — круг, 4 — квадрат,
# 5 — плюс, 6 — шестиугольник, 7 — звезда, 8 — шестиугольник, 9 — влево.
MARKERS_BY_STYLE = {
    1: "^",
    2: ">",
    3: "o",
    4: "s",
    5: "P",
    6: "h",
    7: "*",
    8: "H",
    9: "<",
}


def normalize_column_name(name: str) -> str:
    """Нормализует название колонки для проверки по смыслу."""
    return str(name).strip().lower().replace(" ", "_").replace("-", "_")


RAW_CATEGORICAL_COLUMNS = getattr(dataset, "CATEGORICAL_COLUMNS", set())
RAW_ID_COLUMNS = getattr(dataset, "ID_COLUMNS", {"id", "index", "unnamed: 0"})

CATEGORICAL_COLUMNS = {normalize_column_name(col) for col in RAW_CATEGORICAL_COLUMNS}
ID_COLUMNS = {normalize_column_name(col) for col in RAW_ID_COLUMNS}


def digital_root(number: int) -> int:
    """Рекурсивная сумма цифр до одной цифры."""
    number = abs(int(number))

    while number >= 10:
        number = sum(int(digit) for digit in str(number))

    return number


def marker_for_student_id(student_id: int = STUDENT_ID) -> str:
    """Возвращает маркер точек по студенческому ID."""
    style_number = digital_root(student_id)
    return MARKERS_BY_STYLE[style_number]


def is_id_column(column: str) -> bool:
    """Проверяет, является ли колонка техническим ID/индексом."""
    normalized = normalize_column_name(column)
    return normalized in ID_COLUMNS or normalized.startswith("unnamed")


def is_categorical_column(column: str) -> bool:
    """Проверяет, является ли колонка категориальной по смыслу."""
    normalized = normalize_column_name(column)
    return normalized in CATEGORICAL_COLUMNS


def get_numeric_columns(data: pd.DataFrame | None = None) -> list[str]:
    """Возвращает числовые колонки для кнопок X/Y.

    Для задания №2 исключаются:
    - ID/индексные колонки;
    - категориальные колонки, даже если они записаны числами.

    Наличие пропусков не исключает числовую колонку из интерфейса:
    неполные пары значений отбрасываются на этапе построения конкретного
    графика через ``dropna()``.
    """
    source = dataset.df if data is None else data

    return [
        column
        for column in source.columns
        if is_numeric_dtype(source[column])
        and not is_id_column(column)
        and not is_categorical_column(column)
    ]


def create_scatter_figure(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    marker: str | None = None,
) -> Figure:
    """Создаёт matplotlib Figure с точечной диаграммой."""
    marker = marker or marker_for_student_id()

    if x_col == y_col:
        clean = data[[x_col]].dropna()
        x_values = clean[x_col]
        y_values = clean[x_col]
    else:
        clean = data[[x_col, y_col]].dropna()
        x_values = clean[x_col]
        y_values = clean[y_col]

    figure = Figure(figsize=(6.2, 4.6), dpi=100)
    axis = figure.add_subplot(111)

    axis.scatter(x_values, y_values, marker=marker, alpha=0.75)
    axis.set_xlabel(display_label(x_col))
    axis.set_ylabel(display_label(y_col))
    axis.set_title(f"{display_label(x_col)} / {display_label(y_col)}")
    axis.grid(True, alpha=0.25)

    figure.tight_layout()
    return figure


def figure_to_photo_image(figure: Figure) -> tk.PhotoImage:
    """Преобразует matplotlib Figure в Tkinter PhotoImage."""
    buffer = io.BytesIO()

    canvas = FigureCanvasAgg(figure)
    canvas.draw()
    canvas.print_png(buffer)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return tk.PhotoImage(data=encoded)


def timestamped_graph_name(now: datetime | None = None) -> str:
    """Возвращает имя файла graphHH_MM_SS.png."""
    moment = datetime.now() if now is None else now
    return moment.strftime("graph%H_%M_%S.png")


def build_scatter(
    data: pd.DataFrame,
    x_col: str,
    y_col: str,
    marker: str,
    output_path: Path,
    cat_col: str | None = None,
) -> dict:
    """Строит и сохраняет scatter-график.

    Функция оставлена отдельно, чтобы её можно было проверять тестами.
    В GUI используется create_scatter_figure().
    """
    columns = [x_col]

    if y_col != x_col:
        columns.append(y_col)

    if cat_col is not None and cat_col in data.columns and cat_col not in columns:
        columns.append(cat_col)

    clean = data[columns].dropna()

    figure = create_scatter_figure(clean, x_col, y_col, marker)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300)

    if x_col == y_col:
        correlation = 1.0
    else:
        correlation = clean[x_col].corr(clean[y_col])

    return {
        "x_col": x_col,
        "y_col": y_col,
        "cat_col": cat_col,
        "n_points": len(clean),
        "removed": len(data) - len(clean),
        "correlation": correlation,
    }


class ScatterApplication:
    """Tkinter-приложение для первичной визуализации данных."""

    def __init__(self, root: tk.Tk, data: pd.DataFrame, numeric_columns: Iterable[str]):
        self.root = root
        self.data = data
        self.numeric_columns = list(numeric_columns)

        if len(self.numeric_columns) < 2:
            raise ValueError("Для задания №2 нужны минимум две числовые колонки.")

        self.x_col = self.numeric_columns[0]
        self.y_col = self.numeric_columns[1]
        self.marker = marker_for_student_id()

        self.figure: Figure | None = None
        self._plot_image: tk.PhotoImage | None = None

        self.x_buttons: dict[str, tk.Button] = {}
        self.y_buttons: dict[str, tk.Button] = {}

        self.root.title(WINDOW_TITLE)

        self._build_widgets()
        self.update_plot()

    def _build_widgets(self) -> None:
        main_frame = tk.Frame(self.root, padx=8, pady=8)
        main_frame.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="ns")

        for column in self.numeric_columns:
            button = tk.Button(
                left_frame,
                text=display_label(column),
                width=28,
                command=lambda selected=column: self.select_x(selected),
            )
            button.pack(fill="x", pady=1)
            self.x_buttons[column] = button

        self.canvas = tk.Canvas(
            main_frame,
            width=620,
            height=460,
            bg="white",
            highlightthickness=1,
        )
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        save_frame = tk.Frame(main_frame)
        save_frame.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        save_button = tk.Button(
            save_frame,
            text=SAVE_BUTTON_TEXT,
            command=self.save_current_graph,
        )
        save_button.pack(fill="x")

        bottom_frame = tk.Frame(main_frame)
        bottom_frame.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))

        for index, column in enumerate(self.numeric_columns):
            button = tk.Button(
                bottom_frame,
                text=display_label(column),
                command=lambda selected=column: self.select_y(selected),
            )
            button.grid(row=0, column=index, sticky="ew", padx=1)
            bottom_frame.columnconfigure(index, weight=1)
            self.y_buttons[column] = button

        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def _update_button_states(self) -> None:
        for column, button in self.x_buttons.items():
            button.config(relief=tk.SUNKEN if column == self.x_col else tk.RAISED)

        for column, button in self.y_buttons.items():
            button.config(relief=tk.SUNKEN if column == self.y_col else tk.RAISED)

    def select_x(self, column: str) -> None:
        self.x_col = column
        self.update_plot()

    def select_y(self, column: str) -> None:
        self.y_col = column
        self.update_plot()

    def update_plot(self) -> None:
        self.figure = create_scatter_figure(
            self.data,
            self.x_col,
            self.y_col,
            self.marker,
        )

        self._plot_image = figure_to_photo_image(self.figure)

        self.canvas.delete("all")
        self.canvas.configure(
            width=self._plot_image.width(),
            height=self._plot_image.height(),
        )
        self.canvas.create_image(0, 0, image=self._plot_image, anchor="nw")

        self._update_button_states()

    def save_current_graph(self) -> Path:
        if self.figure is None:
            self.update_plot()

        assert self.figure is not None

        output_path = BASE_DIR / timestamped_graph_name()
        self.figure.savefig(output_path, dpi=300)

        messagebox.showinfo(
            MESSAGEBOX_TITLE,
            f"График сохранён: {output_path.name}",
        )

        return output_path


def main() -> None:
    """Запускает приложение."""
    numeric_columns = get_numeric_columns(dataset.df)

    if len(numeric_columns) < 2:
        raise SystemExit("Недостаточно числовых колонок для построения графика.")

    root = tk.Tk()
    ScatterApplication(root, dataset.df, numeric_columns)
    root.mainloop()


if __name__ == "__main__":
    main()
