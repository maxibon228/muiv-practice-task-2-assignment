"""
data_scatter.py — задание 2 практики.

Окно tkinter с выбором двух числовых колонок и точечной диаграммой.
Категориальные и технические колонки в этом задании игнорируются.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pandas as pd
from PIL import Image, ImageTk

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Для запуска приложения требуется tkinter.") from exc

from data_visual import build_profile, get_scatter_marker, load_dataframe


class DataScatterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("data_scatter.py — первичная визуализация данных")
        self.df = load_dataframe()
        self.profile = build_profile(self.df)
        self.numeric_columns = self.profile.numeric_columns
        if len(self.numeric_columns) < 1:
            raise ValueError("В датасете нет числовых колонок для задания 2.")
        self.x_column = self.numeric_columns[0]
        self.y_column = self.numeric_columns[1] if len(self.numeric_columns) > 1 else self.numeric_columns[0]
        self.width = 620
        self.height = 460
        self.dpi = 100
        self.marker = get_scatter_marker()
        self.status_text = tk.StringVar(value="")
        self.current_image: Optional[Image.Image] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self._build_interface()
        self.update_graph()

    def _build_interface(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        left = ttk.Frame(self.root, padding=(6, 6, 4, 2))
        left.grid(row=0, column=0, sticky="ns")
        ttk.Label(left, text="Y").pack(fill="x")
        for column in self.numeric_columns:
            ttk.Button(left, text=column, command=lambda c=column: self.select_y(c)).pack(fill="x", pady=1)

        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg="white", highlightthickness=1)
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        right = ttk.Frame(self.root, padding=(4, 6, 6, 2))
        right.grid(row=0, column=2, sticky="ns")
        ttk.Button(right, text="Сохранить", command=self.save_graph).pack(fill="x", pady=2)
        ttk.Label(right, textvariable=self.status_text, wraplength=180, justify="left").pack(fill="x", pady=8)

        bottom = ttk.Frame(self.root, padding=(6, 2, 6, 6))
        bottom.grid(row=1, column=0, columnspan=3, sticky="ew")
        ttk.Label(bottom, text="X:").pack(side="left")
        for column in self.numeric_columns:
            ttk.Button(bottom, text=column, command=lambda c=column: self.select_x(c)).pack(side="left", padx=1)

    def select_x(self, column: str) -> None:
        self.x_column = column
        self.update_graph()

    def select_y(self, column: str) -> None:
        self.y_column = column
        self.update_graph()

    def _render_image(self) -> Image.Image:
        fig = Figure(figsize=(self.width / self.dpi, self.height / self.dpi), dpi=self.dpi)
        ax = fig.add_subplot(111)
        # X и Y строятся как независимые Series. Это важно, когда выбрана
        # одна и та же колонка по обеим осям: df[[col, col]] возвращает
        # DataFrame с дублирующимися именами, а не две обычные Series.
        x_series = pd.to_numeric(self.df[self.x_column], errors="coerce")
        y_series = pd.to_numeric(self.df[self.y_column], errors="coerce")
        data = pd.DataFrame({"__x__": x_series, "__y__": y_series}).dropna()
        if data.empty:
            ax.text(0.5, 0.5, "Нет числовых данных", ha="center", va="center")
        else:
            ax.scatter(data["__x__"], data["__y__"], marker=self.marker, alpha=0.85, edgecolors="none")
        ax.set_xlabel(self.x_column)
        ax.set_ylabel(self.y_column)
        ax.set_title("Точечная диаграмма")
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        width, height = canvas.get_width_height()
        return Image.frombuffer("RGBA", (width, height), canvas.buffer_rgba(), "raw", "RGBA", 0, 1).copy()

    def update_graph(self) -> None:
        self.current_image = self._render_image()
        self.tk_image = ImageTk.PhotoImage(self.current_image)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
        self.status_text.set(f"X: {self.x_column}\nY: {self.y_column}\nТип: scatter")

    def save_graph(self, target_path: Optional[Union[str, os.PathLike[str]]] = None) -> Path:
        if self.current_image is None:
            raise RuntimeError("Нечего сохранять: график ещё не построен.")
        path = Path(target_path) if target_path is not None else Path(__file__).resolve().with_name(
            f"graph{datetime.now():%H_%M_%S}.png"
        )
        self.current_image.save(path)
        self.status_text.set(f"График сохранён:\n{path}")
        return path


def main() -> None:
    root = tk.Tk()
    DataScatterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
