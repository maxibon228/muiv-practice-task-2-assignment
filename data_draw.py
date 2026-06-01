"""
data_draw.py — задание 4 практики.

Расширяет data_visual.py режимом ручного рисования поверх графика.
Ctrl+Z отменяет только одну последнюю завершённую линию, как указано в
методических требованиях.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from PIL import Image, ImageDraw

try:
    import tkinter as tk
    from tkinter import colorchooser, ttk
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Для запуска приложения требуется tkinter.") from exc

try:
    from config import STUDENT_ID
except Exception:  # pragma: no cover
    STUDENT_ID = ""

from data_visual import COLORMAP_NAMES, DEFAULT_COLORMAP, DataVisualApp, digital_root


@dataclass
class Stroke:
    """Одна завершённая линия из квадратных отпечатков кисти."""

    color: str
    width: int
    points: list[tuple[int, int]] = field(default_factory=list)
    canvas_item_ids: list[int] = field(default_factory=list)
    deleted: bool = False


def _digits(value: str) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def default_brush_width(student_id: Optional[str] = None) -> int:
    """Рекурсивная сумма цифр ID // 2 + 5."""

    current_id = STUDENT_ID if student_id is None else student_id
    root = digital_root(current_id)
    if root is None:
        return 5
    return root // 2 + 5


def default_brush_rgb(student_id: Optional[str] = None) -> tuple[int, int, int]:
    """Последние 6 цифр ID как RR GG BB."""

    current_id = STUDENT_ID if student_id is None else student_id
    digits = _digits(current_id)
    if not digits:
        return (0, 0, 0)
    last_six = digits[-6:].rjust(6, "0")
    return int(last_six[0:2]), int(last_six[2:4]), int(last_six[4:6])


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


class DataDrawApp(DataVisualApp):
    """Приложение задания 4 с рисованием поверх графиков."""

    def __init__(self, root: tk.Tk):
        self.drawing_enabled = False
        self.current_stroke: Optional[Stroke] = None
        self.strokes: list[Stroke] = []
        self.undo_available = False
        self.last_undo_stroke: Optional[Stroke] = None
        self.brush_color = rgb_to_hex(default_brush_rgb())
        self.brush_width_var: Optional[tk.IntVar] = None
        self.draw_button: Optional[tk.Button] = None
        self.color_button: Optional[tk.Button] = None
        super().__init__(root)
        self.root.title("data_draw.py — визуализация с ручным рисованием")
        self._bind_drawing_events()

    def _build_interface(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)

        top = ttk.Frame(self.root, padding=(6, 6, 6, 2))
        top.grid(row=0, column=0, columnspan=3, sticky="ew")
        ttk.Label(top, text="cmap:").pack(side="left")
        cmap_box = ttk.Combobox(top, textvariable=self.cmap_var, values=COLORMAP_NAMES, width=16, state="readonly")
        cmap_box.pack(side="left", padx=6)
        cmap_box.bind("<<ComboboxSelected>>", lambda _event: self.update_graph())
        ttk.Label(top, text=f"по умолчанию для 'С': {DEFAULT_COLORMAP}").pack(side="left", padx=8)

        draw_panel = ttk.Frame(self.root, padding=(6, 2, 6, 4))
        draw_panel.grid(row=1, column=0, columnspan=3, sticky="ew")

        self.draw_button = tk.Button(draw_panel, text="Рисовать", width=12, command=self.toggle_drawing_mode)
        self.draw_button.pack(side="left", padx=(0, 8))

        ttk.Label(draw_panel, text="Цвет:").pack(side="left")
        self.color_button = tk.Button(
            draw_panel,
            width=3,
            bg=self.brush_color,
            activebackground=self.brush_color,
            command=self.choose_brush_color,
        )
        self.color_button.pack(side="left", padx=(4, 10))

        ttk.Label(draw_panel, text="Толщина:").pack(side="left")
        self.brush_width_var = tk.IntVar(value=default_brush_width())
        width_spin = ttk.Spinbox(draw_panel, from_=1, to=50, width=5, textvariable=self.brush_width_var)
        width_spin.pack(side="left", padx=(4, 12))
        ttk.Label(draw_panel, text="Ctrl+Z — отмена последней линии").pack(side="left", padx=8)

        left = ttk.Frame(self.root, padding=(6, 2, 4, 2))
        left.grid(row=2, column=0, sticky="ns")
        ttk.Label(left, text="Y").pack(fill="x")
        for column in self.profile.columns:
            ttk.Button(left, text=column, command=lambda c=column: self.select_y(c)).pack(fill="x", pady=1)

        self.canvas = tk.Canvas(self.root, width=self.renderer.width, height=self.renderer.height, bg="white", highlightthickness=1)
        self.canvas.grid(row=2, column=1, sticky="nsew", padx=4, pady=4)

        right = ttk.Frame(self.root, padding=(4, 2, 6, 2))
        right.grid(row=2, column=2, sticky="ns")
        ttk.Button(right, text="Сохранить", command=self.save_graph).pack(fill="x", pady=2)
        ttk.Label(right, textvariable=self.status_text, wraplength=190, justify="left").pack(fill="x", pady=8)

        bottom = ttk.Frame(self.root, padding=(6, 2, 6, 6))
        bottom.grid(row=3, column=0, columnspan=3, sticky="ew")
        ttk.Label(bottom, text="X:").pack(side="left")
        for column in self.profile.columns:
            ttk.Button(bottom, text=column, command=lambda c=column: self.select_x(c)).pack(side="left", padx=1)

    def _bind_drawing_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.extend_stroke)
        self.canvas.bind("<ButtonRelease-1>", self.finish_stroke)
        self.root.bind("<ButtonRelease-1>", self.finish_stroke)
        self.canvas.bind("<ButtonPress-3>", self.disable_drawing_mode)
        self.root.bind("<Control-z>", self.undo_last_stroke)
        self.root.bind("<Control-Z>", self.undo_last_stroke)

    def select_x(self, column: str) -> None:
        self.disable_drawing_mode()
        self.x_column = column
        self.update_graph()

    def select_y(self, column: str) -> None:
        self.disable_drawing_mode()
        self.y_column = column
        self.update_graph()

    def update_graph(self) -> None:
        self.disable_drawing_mode()
        self.strokes.clear()
        self.current_stroke = None
        self.undo_available = False
        self.last_undo_stroke = None
        super().update_graph()
        self._update_status_with_brush()

    def _update_status_with_brush(self) -> None:
        if self.current_result is None:
            return
        mode = "вкл" if self.drawing_enabled else "выкл"
        undo = "доступна" if self.undo_available else "нет"
        self.status_text.set(
            f"X: {self.x_column}\n"
            f"Y: {self.y_column}\n"
            f"Тип: {self.current_result.plot_kind}\n"
            f"Cmap: {self.current_result.cmap_name}\n"
            f"Рисование: {mode}\n"
            f"Кисть: {self.brush_color}, {self.get_brush_width()}px\n"
            f"Ctrl+Z: {undo}"
        )

    def get_brush_width(self) -> int:
        if self.brush_width_var is None:
            return default_brush_width()
        try:
            value = int(self.brush_width_var.get())
        except Exception:
            value = default_brush_width()
        return max(1, min(50, value))

    def choose_brush_color(self) -> None:
        chosen = colorchooser.askcolor(color=self.brush_color, title="Выбор цвета кисти")
        if chosen and chosen[1]:
            self.brush_color = str(chosen[1])
            if self.color_button is not None:
                self.color_button.configure(bg=self.brush_color, activebackground=self.brush_color)
            self._update_status_with_brush()

    def toggle_drawing_mode(self) -> None:
        if self.drawing_enabled:
            self.disable_drawing_mode()
        else:
            self.enable_drawing_mode()

    def enable_drawing_mode(self) -> None:
        self.drawing_enabled = True
        if self.draw_button is not None:
            self.draw_button.configure(relief="sunken")
        try:
            self.canvas.configure(cursor="pencil")
        except tk.TclError:
            self.canvas.configure(cursor="crosshair")
        self._update_status_with_brush()

    def disable_drawing_mode(self, event=None) -> None:
        del event
        if self.current_stroke is not None:
            self._delete_canvas_items(self.current_stroke)
            self.current_stroke = None
        self.drawing_enabled = False
        if self.draw_button is not None:
            self.draw_button.configure(relief="raised")
        if hasattr(self, "canvas"):
            self.canvas.configure(cursor="")
        self._update_status_with_brush()

    def _event_inside_canvas(self, event) -> bool:
        return 0 <= int(event.x) < self.renderer.width and 0 <= int(event.y) < self.renderer.height

    def start_stroke(self, event) -> None:
        if not self.drawing_enabled or not self._event_inside_canvas(event):
            return
        stroke = Stroke(color=self.brush_color, width=self.get_brush_width())
        self.current_stroke = stroke
        self._stamp_point(event.x, event.y, stroke)

    def extend_stroke(self, event) -> None:
        if not self.drawing_enabled or self.current_stroke is None or not self._event_inside_canvas(event):
            return
        self._stamp_point(event.x, event.y, self.current_stroke)

    def finish_stroke(self, event=None) -> None:
        del event
        if self.current_stroke is None:
            return
        if self.current_stroke.points:
            self.strokes.append(self.current_stroke)
            self.last_undo_stroke = self.current_stroke
            self.undo_available = True
        self.current_stroke = None
        self._update_status_with_brush()

    def _stamp_point(self, x: int, y: int, stroke: Stroke) -> None:
        x = max(0, min(self.renderer.width - 1, int(x)))
        y = max(0, min(self.renderer.height - 1, int(y)))
        item_id = self._draw_stamp(x, y, stroke)
        stroke.canvas_item_ids.append(item_id)
        stroke.points.append((x, y))

    def _draw_stamp(self, x: int, y: int, stroke: Stroke) -> int:
        half = max(0, stroke.width // 2)
        left = max(0, x - half)
        top = max(0, y - half)
        right = min(self.renderer.width, x + half)
        bottom = min(self.renderer.height, y + half)
        return self.canvas.create_rectangle(left, top, right, bottom, fill=stroke.color, outline=stroke.color, width=0)

    def _delete_canvas_items(self, stroke: Stroke) -> None:
        for item_id in stroke.canvas_item_ids:
            self.canvas.delete(item_id)
        stroke.canvas_item_ids.clear()

    def undo_last_stroke(self, event=None) -> None:
        del event
        if self.current_stroke is not None:
            return
        if not self.undo_available or self.last_undo_stroke is None or self.last_undo_stroke.deleted:
            return
        self._delete_canvas_items(self.last_undo_stroke)
        self.last_undo_stroke.deleted = True
        self.undo_available = False
        self.last_undo_stroke = None
        self._update_status_with_brush()

    def _compose_image_with_strokes(self) -> Image.Image:
        if self.current_result is None:
            raise RuntimeError("Нечего сохранять: график ещё не построен.")
        image = self.current_result.image.convert("RGBA").copy()
        draw = ImageDraw.Draw(image)
        for stroke in self.strokes:
            if stroke.deleted:
                continue
            half = max(0, stroke.width // 2)
            for x, y in stroke.points:
                left = max(0, x - half)
                top = max(0, y - half)
                right = min(image.width, x + half)
                bottom = min(image.height, y + half)
                draw.rectangle([left, top, right, bottom], fill=stroke.color)
        return image

    def save_graph(self, target_path: Optional[Union[str, os.PathLike[str]]] = None) -> Path:
        path = Path(target_path) if target_path is not None else Path(__file__).resolve().with_name(
            f"graph{datetime.now():%H_%M_%S}.png"
        )
        image = self._compose_image_with_strokes()
        image.save(path)
        self.status_text.set(f"График сохранён:\n{path}")
        return path

    def run_smoke_test(self, output_path: Union[str, os.PathLike[str]]) -> Path:
        self.enable_drawing_mode()
        fake = type("Event", (), {})
        start = fake(); start.x, start.y = 40, 40
        self.start_stroke(start)
        for x, y in [(60, 60), (80, 80), (100, 100), (120, 120)]:
            event = fake(); event.x, event.y = x, y
            self.extend_stroke(event)
        self.finish_stroke()
        return self.save_graph(output_path)


def smoke_test(output_path: str, auto_close_ms: int) -> None:
    root = tk.Tk()
    app = DataDrawApp(root)
    path = app.run_smoke_test(output_path)
    root.after(auto_close_ms, root.destroy)
    root.mainloop()
    print(f"SMOKE_OK {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="data_draw.py — задание 4 практики")
    parser.add_argument("--smoke-test", action="store_true", help="запустить автоматическую GUI-проверку и выйти")
    parser.add_argument("--smoke-output", default="test_outputs/manual_smoke.png", help="куда сохранить PNG smoke-теста")
    parser.add_argument("--auto-close-ms", type=int, default=100, help="задержка закрытия окна smoke-теста")
    args = parser.parse_args()

    if args.smoke_test:
        Path(args.smoke_output).parent.mkdir(parents=True, exist_ok=True)
        smoke_test(args.smoke_output, args.auto_close_ms)
        return

    root = tk.Tk()
    DataDrawApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
