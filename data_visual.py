"""
data_visual.py — задание 3 практики.

Приложение строит график по двум выбранным колонкам датасета и автоматически
выбирает тип визуализации:
- одинаковая числовая колонка по X и Y -> гистограмма;
- одинаковая категориальная колонка по X и Y -> круговая диаграмма;
- X категориальная, Y любая другая -> столбчатая диаграмма количества;
- X числовая, Y категориальная -> коробочная диаграмма;
- остальные сочетания -> точечная диаграмма.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, Union

import matplotlib
matplotlib.use("Agg")
from matplotlib import colormaps
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pandas as pd
from PIL import Image, ImageTk

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Для запуска приложения требуется tkinter.") from exc

try:
    from config import MARKERS_BY_DIGITAL_ROOT, STUDENT_ID, SURNAME_FIRST_LETTER
except Exception:  # pragma: no cover
    MARKERS_BY_DIGITAL_ROOT = {1: "^", 2: ">", 3: "o", 4: "s", 5: "P", 6: "h", 7: "*", 8: "H", 9: "<"}
    STUDENT_ID = ""
    SURNAME_FIRST_LETTER = "С"

PlotKind = Literal["scatter", "hist", "pie", "bar", "box"]

COLORMAPS_BY_LETTER = {
    "А": "viridis", "Б": "plasma", "В": "inferno", "Г": "magma", "Д": "cividis",
    "Е": "Greys", "Ё": "Greys", "Ж": "Purples", "З": "Blues", "И": "Greens",
    "Й": "Oranges", "К": "Reds", "Л": "YlOrBr", "М": "YlOrRd", "Н": "OrRd",
    "О": "PuRd", "П": "RdPu", "Р": "BuPu", "С": "GnBu", "Т": "PuBu",
    "У": "YlGnBu", "Ф": "PuBuGn", "Х": "BuGn", "Ц": "YlGn", "Ч": "binary",
    "Ш": "gist_yarg", "Щ": "spring", "Э": "summer", "Ю": "autumn", "Я": "winter",
}

COLORMAP_NAMES = [
    "viridis", "plasma", "inferno", "magma", "cividis", "Greys", "Purples", "Blues",
    "Greens", "Oranges", "Reds", "YlOrBr", "YlOrRd", "OrRd", "PuRd", "RdPu", "BuPu",
    "GnBu", "PuBu", "YlGnBu", "PuBuGn", "BuGn", "YlGn", "binary", "gist_yarg",
    "spring", "summer", "autumn", "winter",
]

DEFAULT_COLORMAP = COLORMAPS_BY_LETTER.get(str(SURNAME_FIRST_LETTER).upper(), "GnBu")

FORCED_CATEGORICAL_NAMES = {
    "sex", "gender", "smoking", "death", "survived", "survivor", "выжил", "пол",
    "class", "pclass", "класспассажира", "портзагрузки", "embarked",
}
CATEGORICAL_NAME_HINTS = {
    "sex", "gender", "smoking", "death", "survived", "survivor", "class", "pclass", "embarked",
    "категор", "класс", "порт", "выжил", "пол", "пережил",
}
COUNT_NUMERIC_HINTS = {
    "count", "number", "amount", "quantity", "количество", "сколько", "взросл", "дет",
    "children", "adult", "sibsp", "parch",
}
MEASUREMENT_NUMERIC_HINTS = {
    "age", "возраст", "fare", "стоимость", "price", "platelet", "platelets", "serum",
    "creatinine", "sodium", "fraction", "ejection", "phosphokinase", "pressure", "time",
    "время", "рост", "вес", "height", "weight",
}
TECHNICAL_EXACT_NAMES = {"id", "index", "номер"}
TECHNICAL_PREFIXES = ("unnamed",)


@dataclass(frozen=True)
class DataProfile:
    columns: list[str]
    numeric_columns: list[str]
    categorical_columns: list[str]


@dataclass
class RenderResult:
    image: Image.Image
    plot_kind: PlotKind
    x_column: str
    y_column: str
    cmap_name: str


def normalize_column_name(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", str(name).strip().lower())


def is_technical_column(name: str) -> bool:
    normalized = normalize_column_name(name)
    return normalized in TECHNICAL_EXACT_NAMES or normalized.startswith(TECHNICAL_PREFIXES)


def digital_root(value: str) -> Optional[int]:
    digits = [int(ch) for ch in str(value) if ch.isdigit()]
    if not digits:
        return None
    number = sum(digits)
    while number > 9:
        number = sum(int(ch) for ch in str(number))
    return number


def get_scatter_marker() -> str:
    root = digital_root(STUDENT_ID)
    if root is None:
        return "o"
    return MARKERS_BY_DIGITAL_ROOT.get(root, "o")


def load_dataframe() -> pd.DataFrame:
    """Загрузить данные из dataset.df или из dataset.csv рядом с программой."""
    try:
        import dataset  # type: ignore
        frame = getattr(dataset, "df", None)
        if isinstance(frame, pd.DataFrame):
            return frame.copy()
    except Exception:
        pass

    csv_path = Path(__file__).resolve().with_name("dataset.csv")
    if not csv_path.exists():
        raise FileNotFoundError("Не найден dataset.csv рядом с программой.")
    return pd.read_csv(csv_path)


def is_integer_like(series: pd.Series) -> bool:
    numeric = pd.to_numeric(series.dropna(), errors="coerce").dropna()
    if numeric.empty:
        return False
    return bool((numeric % 1 == 0).all())


def is_categorical_column(name: str, series: pd.Series, row_count: int) -> bool:
    del row_count
    normalized = normalize_column_name(name)

    if is_technical_column(name):
        return False
    if normalized in FORCED_CATEGORICAL_NAMES:
        return True
    if any(hint in normalized for hint in CATEGORICAL_NAME_HINTS):
        return True
    if not pd.api.types.is_numeric_dtype(series):
        return True
    if any(hint in normalized for hint in COUNT_NUMERIC_HINTS):
        return False
    if any(hint in normalized for hint in MEASUREMENT_NUMERIC_HINTS):
        return False

    unique_count = int(series.dropna().nunique())
    # Автоопределение оставлено осторожным: только совсем маленькие целочисленные коды.
    return 0 < unique_count <= 5 and is_integer_like(series)


def build_profile(df: pd.DataFrame) -> DataProfile:
    columns: list[str] = []
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []

    for column_obj in df.columns:
        column = str(column_obj)
        if is_technical_column(column):
            continue
        columns.append(column)
        series = df[column_obj]
        if is_categorical_column(column, series, len(df)):
            categorical_columns.append(column)
        elif pd.api.types.is_numeric_dtype(series):
            numeric_columns.append(column)
        else:
            categorical_columns.append(column)

    return DataProfile(columns=columns, numeric_columns=numeric_columns, categorical_columns=categorical_columns)


def choose_plot_kind(profile: DataProfile, x_column: str, y_column: str) -> PlotKind:
    x_is_cat = x_column in profile.categorical_columns
    y_is_cat = y_column in profile.categorical_columns
    x_is_num = x_column in profile.numeric_columns
    y_is_num = y_column in profile.numeric_columns

    # Самая важная ветка: одинаковая категориальная колонка всегда pie.
    if x_column == y_column:
        if x_is_cat or y_is_cat:
            return "pie"
        if x_is_num or y_is_num:
            return "hist"
    if x_is_cat and x_column != y_column:
        return "bar"
    if x_is_num and y_is_cat:
        return "box"
    if x_is_num and y_is_num:
        return "scatter"
    return "scatter"


def colors_from_cmap(cmap_name: str, count: int) -> list:
    cmap = colormaps.get_cmap(cmap_name)
    if count <= 0:
        return []
    if count == 1:
        return [cmap(0.65)]
    return [cmap(index / (count - 1)) for index in range(count)]


def sorted_counts(series: pd.Series) -> pd.Series:
    counts = series.dropna().value_counts()
    try:
        return counts.sort_index()
    except Exception:
        return counts.sort_index(key=lambda idx: idx.astype(str))


class PlotRenderer:
    def __init__(self, df: pd.DataFrame, profile: DataProfile, width: int = 620, height: int = 460):
        self.df = df
        self.profile = profile
        self.width = width
        self.height = height
        self.dpi = 100
        self.scatter_marker = get_scatter_marker()

    def render(self, x_column: str, y_column: str, cmap_name: str) -> RenderResult:
        plot_kind = choose_plot_kind(self.profile, x_column, y_column)
        fig = Figure(figsize=(self.width / self.dpi, self.height / self.dpi), dpi=self.dpi)
        ax = fig.add_subplot(111)

        if plot_kind == "hist":
            self._draw_hist(ax, x_column, cmap_name)
        elif plot_kind == "pie":
            self._draw_pie(ax, x_column, cmap_name)
        elif plot_kind == "bar":
            self._draw_bar(ax, x_column, cmap_name)
        elif plot_kind == "box":
            self._draw_box(ax, x_column, y_column, cmap_name)
        else:
            self._draw_scatter(ax, x_column, y_column, cmap_name)

        fig.tight_layout()
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        width, height = canvas.get_width_height()
        image = Image.frombuffer("RGBA", (width, height), canvas.buffer_rgba(), "raw", "RGBA", 0, 1).copy()
        return RenderResult(image=image, plot_kind=plot_kind, x_column=x_column, y_column=y_column, cmap_name=cmap_name)

    def _draw_scatter(self, ax, x_column: str, y_column: str, cmap_name: str) -> None:
        data = self.df[[x_column, y_column]].copy()
        data[x_column] = pd.to_numeric(data[x_column], errors="coerce")
        data[y_column] = pd.to_numeric(data[y_column], errors="coerce")
        data = data.dropna()
        if data.empty:
            ax.text(0.5, 0.5, "Нет числовых данных для точечной диаграммы", ha="center", va="center")
        else:
            ax.scatter(data[x_column], data[y_column], c=list(range(len(data))), cmap=cmap_name,
                       marker=self.scatter_marker, alpha=0.85, edgecolors="none")
        ax.set_xlabel(x_column)
        ax.set_ylabel(y_column)
        ax.set_title("Точечная диаграмма")
        ax.grid(True, alpha=0.25)

    def _draw_hist(self, ax, column: str, cmap_name: str) -> None:
        values = pd.to_numeric(self.df[column], errors="coerce").dropna()
        if values.empty:
            ax.text(0.5, 0.5, "Нет числовых данных для гистограммы", ha="center", va="center")
        else:
            counts, _bins, patches = ax.hist(values, bins=10, edgecolor="black", linewidth=0.4)
            for patch, color in zip(patches, colors_from_cmap(cmap_name, len(patches))):
                patch.set_facecolor(color)
            for count, patch in zip(counts, patches):
                if count > 0:
                    ax.text(patch.get_x() + patch.get_width() / 2, count, str(int(count)),
                            ha="center", va="bottom", fontsize=8)
        ax.set_xlabel(column)
        ax.set_ylabel("Количество")
        ax.set_title("Гистограмма")
        ax.grid(True, axis="y", alpha=0.25)

    def _draw_pie(self, ax, column: str, cmap_name: str) -> None:
        counts = sorted_counts(self.df[column])
        if counts.empty:
            ax.text(0.5, 0.5, "Нет категориальных данных", ha="center", va="center")
        else:
            labels = [str(item) for item in counts.index]
            total = int(counts.sum())

            def absolute_count_label(percent: float) -> str:
                value = int(round(percent * total / 100)) if total else 0
                return str(value) if value > 0 else ""

            ax.pie(counts.values, labels=labels, autopct=absolute_count_label,
                   colors=colors_from_cmap(cmap_name, len(counts)), startangle=90,
                   pctdistance=0.70, labeldistance=1.08, textprops={"fontsize": 9})
            ax.axis("equal")
        ax.set_title(f"Круговая диаграмма: {column}")

    def _draw_bar(self, ax, category_column: str, cmap_name: str) -> None:
        counts = sorted_counts(self.df[category_column])
        if counts.empty:
            ax.text(0.5, 0.5, "Нет категориальных данных", ha="center", va="center")
        else:
            labels = [str(item) for item in counts.index]
            bars = ax.bar(labels, counts.values, color=colors_from_cmap(cmap_name, len(counts)))
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2, height, str(int(height)),
                        ha="center", va="bottom", fontsize=8)
        ax.set_xlabel(category_column)
        ax.set_ylabel("Количество")
        ax.set_title("Столбчатая диаграмма")
        ax.grid(True, axis="y", alpha=0.25)

    def _draw_box(self, ax, numeric_column: str, category_column: str, cmap_name: str) -> None:
        data = self.df[[numeric_column, category_column]].copy()
        data[numeric_column] = pd.to_numeric(data[numeric_column], errors="coerce")
        data = data.dropna()
        grouped = list(data.groupby(category_column, sort=True))
        labels = [str(label) for label, _group in grouped]
        groups = [group[numeric_column].to_numpy() for _label, group in grouped]
        if not groups:
            ax.text(0.5, 0.5, "Нет данных для коробочной диаграммы", ha="center", va="center")
        else:
            try:
                boxplot = ax.boxplot(groups, tick_labels=labels, patch_artist=True, vert=False)
            except TypeError:  # старые версии matplotlib
                boxplot = ax.boxplot(groups, labels=labels, patch_artist=True, vert=False)
            for patch, color in zip(boxplot["boxes"], colors_from_cmap(cmap_name, len(groups))):
                patch.set_facecolor(color)
                patch.set_alpha(0.85)
        ax.set_xlabel(numeric_column)
        ax.set_ylabel(category_column)
        ax.set_title("Коробочная диаграмма")
        ax.grid(True, axis="x", alpha=0.25)


class DataVisualApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("data_visual.py — улучшенная визуализация данных")
        self.df = load_dataframe()
        self.profile = build_profile(self.df)
        if not self.profile.columns:
            raise ValueError("В датасете нет колонок для визуализации.")

        self.x_column = self.profile.columns[0]
        self.y_column = self.profile.columns[1] if len(self.profile.columns) > 1 else self.profile.columns[0]
        self.cmap_var = tk.StringVar(value=DEFAULT_COLORMAP)
        self.status_text = tk.StringVar(value="")
        self.renderer = PlotRenderer(self.df, self.profile)
        self.current_result: Optional[RenderResult] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self._build_interface()
        self.update_graph()

    def _build_interface(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        top = ttk.Frame(self.root, padding=(6, 6, 6, 2))
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(top, text="cmap:").pack(side="left")
        cmap_box = ttk.Combobox(top, textvariable=self.cmap_var, values=COLORMAP_NAMES, width=16, state="readonly")
        cmap_box.pack(side="left", padx=6)
        cmap_box.bind("<<ComboboxSelected>>", lambda _event: self.update_graph())
        ttk.Label(top, text=f"по умолчанию для 'С': {DEFAULT_COLORMAP}").pack(side="left", padx=8)

        left = ttk.Frame(self.root, padding=(6, 2, 4, 2))
        left.grid(row=1, column=0, sticky="ns")
        ttk.Label(left, text="Y").pack(fill="x")
        for column in self.profile.columns:
            ttk.Button(left, text=column, command=lambda c=column: self.select_y(c)).pack(fill="x", pady=1)

        self.canvas = tk.Canvas(self.root, width=self.renderer.width, height=self.renderer.height, bg="white", highlightthickness=1)
        self.canvas.grid(row=1, column=1, sticky="nsew", padx=4, pady=4)

        right = ttk.Frame(self.root, padding=(4, 2, 6, 2))
        right.grid(row=1, column=2, sticky="ns")
        ttk.Button(right, text="Сохранить", command=self.save_graph).pack(fill="x", pady=2)
        ttk.Label(right, textvariable=self.status_text, wraplength=190, justify="left").pack(fill="x", pady=8)

        bottom = ttk.Frame(self.root, padding=(6, 2, 6, 6))
        bottom.grid(row=2, column=0, columnspan=3, sticky="ew")
        ttk.Label(bottom, text="X:").pack(side="left")
        for column in self.profile.columns:
            ttk.Button(bottom, text=column, command=lambda c=column: self.select_x(c)).pack(side="left", padx=1)

    def select_x(self, column: str) -> None:
        self.x_column = column
        self.update_graph()

    def select_y(self, column: str) -> None:
        self.y_column = column
        self.update_graph()

    def update_graph(self) -> None:
        cmap_name = self.cmap_var.get() or DEFAULT_COLORMAP
        self.current_result = self.renderer.render(self.x_column, self.y_column, cmap_name)
        self.tk_image = ImageTk.PhotoImage(self.current_result.image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.status_text.set(f"X: {self.x_column}\nY: {self.y_column}\nТип: {self.current_result.plot_kind}\nCmap: {cmap_name}")

    def save_graph(self, target_path: Optional[Union[str, os.PathLike[str]]] = None) -> Path:
        if self.current_result is None:
            raise RuntimeError("Нечего сохранять: график ещё не построен.")
        path = Path(target_path) if target_path is not None else Path(__file__).resolve().with_name(
            f"graph{datetime.now():%H_%M_%S}.png"
        )
        self.current_result.image.save(path)
        self.status_text.set(f"График сохранён:\n{path}")
        return path


def main() -> None:
    root = tk.Tk()
    DataVisualApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
