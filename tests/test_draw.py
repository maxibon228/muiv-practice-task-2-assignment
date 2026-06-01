from pathlib import Path
import tkinter as tk
from data_draw import DataDrawApp, default_brush_width, default_brush_rgb, rgb_to_hex

def test_formulas():
    assert default_brush_width('70123456') == 5
    assert default_brush_rgb('70123456') == (12, 34, 56)
    assert rgb_to_hex((12, 34, 56)) == '#0c2238'

def test_draw_smoke_and_undo(tmp_path):
    root = tk.Tk(); root.withdraw()
    app = DataDrawApp(root)
    saved = app.run_smoke_test(tmp_path / 'draw.png')
    assert saved.exists() and saved.stat().st_size > 0
    assert len(app.strokes) == 1
    app.undo_last_stroke()
    assert app.strokes[-1].deleted is True
    app.undo_last_stroke()
    assert len([s for s in app.strokes if s.deleted]) == 1
    root.destroy()

def test_pie_regression():
    root = tk.Tk(); root.withdraw()
    app = DataDrawApp(root)
    c = app.profile.categorical_columns[0]
    app.select_x(c); app.select_y(c)
    assert app.current_result.plot_kind == 'pie'
    root.destroy()
