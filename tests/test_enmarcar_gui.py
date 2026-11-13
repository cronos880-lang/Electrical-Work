"""Regresión funcional de Enmarcar con eventos reales de Tkinter.

Ejecutar con entorno gráfico: python -m unittest discover -s tests -v
En Linux sin pantalla: xvfb-run -a python -m unittest discover -s tests -v
No se añaden bibliotecas externas.
"""
from __future__ import annotations

import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import make_symbol, make_straight_wire
from electrical_work import ElectricalWorkApp


class TestEnmarcarGUI(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tkinter sin pantalla disponible: {exc}")
        self.root.geometry("1280x900")
        self.app = ElectricalWorkApp(self.root)
        self.root.update()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def _fixture(self):
        a = make_symbol("contact_no", 300, 220)
        b = make_symbol("contact_nc", 460, 290)
        c = make_symbol("contact_no", 900, 620)
        self.app.doc["elements"] = [a, b, c]
        self.app.doc["wires"] = []
        self.app.redraw()
        self.root.update()
        return a, b, c

    def _enmarcar_from_second_button(self):
        self.app._toggle_tool_group("wire_group")
        self.root.update()
        self.assertEqual(self.app._groups["wire_group"][1], "select_box")
        button = self.app._flyout_buttons["select_box"]
        button.event_generate("<ButtonPress-1>", x=12, y=12)
        self.assertNotEqual(self.app.tool, "select_box",
                            "La pulsación aún no debe destruir el desplegable")
        self.assertTrue(button.winfo_exists())
        button.event_generate("<ButtonRelease-1>", x=12, y=12)
        self.root.update()
        self.assertEqual(self.app.tool, "select_box")

    def _mouse_at_page(self, x, y):
        cv = self.app.canvas
        px, py = self.app._xy(x, y)
        return round(px - cv.canvasx(0)), round(py - cv.canvasy(0))

    def _drag_rectangle(self, x1, y1, x2, y2):
        cv = self.app.canvas
        ax, ay = self._mouse_at_page(x1, y1)
        bx, by = self._mouse_at_page(x2, y2)
        mx, my = round((ax + bx) / 2), round((ay + by) / 2)
        cv.event_generate("<ButtonPress-1>", x=ax, y=ay)
        cv.event_generate("<B1-Motion>", x=mx, y=my)
        self.assertEqual(self.app.tool, "select_box")
        self.assertIsNotNone(self.app.marquee_start)
        self.assertTrue(cv.find_withtag("selection-marquee"))
        cv.event_generate("<B1-Motion>", x=bx, y=by)
        cv.event_generate("<ButtonRelease-1>", x=bx, y=by)
        self.root.update()
        self.assertIsNone(self.app.marquee_start)
        self.assertEqual(self.app.tool, "select_box",
                         "Un recuadro terminado no debe activar Puntero")

    def test_second_icon_selects_two_and_remains_active(self):
        a, b, c = self._fixture()
        self._enmarcar_from_second_button()
        canvas = self.app.canvas
        offset = (canvas.canvasx(0), canvas.canvasy(0))
        self._drag_rectangle(245, 160, 525, 355)
        expected = {("element", a["id"]), ("element", b["id"])}
        self.assertEqual(self.app._selection_items(), expected)
        self.assertEqual((canvas.canvasx(0), canvas.canvasy(0)), offset,
                         "Enmarcar no puede desplazar la vista")
        self.assertFalse(self.app.dirty, "Seleccionar no modifica el proyecto")
        self._drag_rectangle(250, 165, 355, 255)
        self.assertEqual(self.app._selection_items(), {("element", a["id"])})
        self.assertEqual(self.app.tool, "select_box")

    def test_cable_crossing_frame_and_escape_preserves_selection(self):
        self._fixture()
        wire = make_straight_wire((200, 430), (760, 430))
        self.app.doc["wires"].append(wire)
        self.app.redraw()
        self.root.update()
        self._enmarcar_from_second_button()
        self._drag_rectangle(350, 400, 510, 460)
        self.assertIn(("wire", wire["id"]), self.app._selection_items())
        self.app.return_to_pointer()
        self.assertEqual(self.app.tool, "select")
        self.assertIn(("wire", wire["id"]), self.app._selection_items())

    def test_zoom_selection_does_not_pan(self):
        a, b, c = self._fixture()
        self.app.set_zoom(240)
        self.app.canvas.xview_moveto(0)
        self.app.canvas.yview_moveto(0)
        self.root.update()
        self._enmarcar_from_second_button()
        before = (self.app.canvas.canvasx(0), self.app.canvas.canvasy(0))
        self._drag_rectangle(250, 170, 352, 263)
        self.assertEqual(self.app._selection_items(), {("element", a["id"])})
        self.assertEqual(before, (self.app.canvas.canvasx(0),
                                  self.app.canvas.canvasy(0)))


if __name__ == "__main__":
    unittest.main()
