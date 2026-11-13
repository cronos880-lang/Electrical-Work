"""Regresión visual del editor compacto, sin tocar proyectos .ework.

Ejecución: python -m unittest discover -s tests -v
En Windows comprueba widgets reales; sin pantalla salta las pruebas Tk.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from electrical_work import ElectricalWorkApp


def widgets_of_type(parent, klass):
    found = []
    for child in parent.winfo_children():
        if isinstance(child, klass):
            found.append(child)
        found.extend(widgets_of_type(child, klass))
    return found


class TestVisualPolish(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"No hay pantalla disponible para Tkinter: {exc}")
        self.root.geometry("1460x900")
        self.app = ElectricalWorkApp(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def test_cabecera_afinada_y_cuatro_componentes_inalterados(self):
        labels = widgets_of_type(self.root, tk.Label)
        title = [x for x in labels if x.cget("text") == "Electrical Work · Compacto"]
        subtitle = [x for x in labels if x.cget("text")
                    == "Editor de esquemas · 70 % · V0.5.2"]
        self.assertEqual(len(title), 1)
        self.assertEqual(len(subtitle), 1)
        self.assertEqual(tkfont.Font(root=self.root, font=title[0].cget("font")).actual("weight"), "normal")
        self.assertIn("COMPACTO V0.5.2", self.root.title())
        self.assertEqual(self.app._groups["wire_group"][0:2],
                         ("wire_straight", "select_box"))
        buttons = [b.cget("text") for b in widgets_of_type(self.root, tk.Button)]
        for action in ("Nuevo", "Abrir", "Guardar", "Documentación",
                       "Exportar PDF", "Salir"):
            self.assertIn(action, buttons)

    def test_icono_vectorial_sin_imagen_externa(self):
        canvases = widgets_of_type(self.root, tk.Canvas)
        badge = [c for c in canvases if int(c.cget("width")) == 43
                 and int(c.cget("height")) == 43]
        self.assertEqual(len(badge), 1)
        self.assertGreaterEqual(len(badge[0].find_all()), 5)
        self.assertEqual(self.app.tool, "select")
        self.assertFalse(self.app.dirty)
        self.assertFalse(self.app.doc["elements"])
        self.assertFalse(self.app.doc["wires"])


if __name__ == "__main__":
    unittest.main()
