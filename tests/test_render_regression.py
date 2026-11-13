"""Regresión gráfica del editor compacto. Python >= 3.9, sin dependencias nuevas.

Ejecutar: python -m unittest discover -s tests -v
Pillow solo es necesario para la prueba opcional de suavizado.
"""
from __future__ import annotations
import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core import (SYMBOL_NAMES, COMPACT_SCALE, GRID, make_symbol, new_project,
                  port_positions, symbol_shapes, save_project, load_project, export_svg)
from pdf_export import export_project_pdf
import quality_render


def numbers(shape):
    if shape[0] in ('line', 'dashline', 'circle', 'dot'):
        return shape[1:]
    if shape[0] in ('polygon', 'filledpolygon'):
        return (n for point in shape[1] for n in point)
    if shape[0] in ('text', 'textcenter', 'textend'):
        return (shape[1], shape[2], shape[4])
    return ()


def near(a, b):
    return abs(a[0] - b[0]) < .11 and abs(a[1] - b[1]) < .11


class GraphicsRegression(unittest.TestCase):
    def test_symbols_compatible_with_ports_and_grid(self):
        for kind in SYMBOL_NAMES:
            for angle in (0, 90, 180, 270):
                with self.subTest(kind=kind, angle=angle):
                    item=make_symbol(kind, 600, 430, rotation=angle,
                                     draw_scale=COMPACT_SCALE)
                    before=copy.deepcopy(item)
                    ports=port_positions(item)
                    shapes=symbol_shapes(item, include_annotations=False)
                    self.assertTrue(shapes)
                    self.assertEqual(before, item)
                    self.assertEqual(ports, port_positions(item))
                    self.assertTrue(all(math.isfinite(n) for sh in shapes
                                        for n in numbers(sh)))
                    self.assertTrue(all(abs(c/GRID-round(c/GRID)) < 1e-7
                                        for xy in ports for c in xy))
                    if kind in ('terminal','junction','ground','motor_1ph','motor_3ph'):
                        continue
                    for port in ports:
                        self.assertTrue(any(sh[0] in ('line','dashline') and
                                            (near(sh[1:3],port) or near(sh[3:5],port))
                                            for sh in shapes), (kind, angle, port))

    def test_sensor_na_nc_are_visually_distinguishable(self):
        for family in ('inductive','capacitive','magnetic'):
            a=make_symbol('sensor_'+family+'_no', 500, 400,
                          draw_scale=COMPACT_SCALE)
            b=make_symbol('sensor_'+family+'_nc', 500, 400,
                          draw_scale=COMPACT_SCALE)
            self.assertNotEqual(symbol_shapes(a,include_annotations=False),
                                symbol_shapes(b,include_annotations=False))
            self.assertEqual(port_positions(a),port_positions(b))

    def test_project_roundtrip_and_vector_exports(self):
        project=new_project('Regresion de simbologia')
        for i,kind in enumerate(SYMBOL_NAMES):
            item=make_symbol(kind,120+(i%7)*155,100+(i//7)*82,
                             draw_scale=COMPACT_SCALE,label='T'+str(i))
            project['sheets'][0]['elements'].append(item)
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)
            path=folder/'regression.ework'
            save_project(project,path)
            result=load_project(path)
            original=project['sheets'][0]['elements']
            recovered=result['sheets'][0]['elements']
            self.assertEqual(original,recovered)
            for a,b in zip(original,recovered):
                self.assertEqual(port_positions(a),port_positions(b))
            svg=folder/'a.svg'
            pdf=folder/'a.pdf'
            export_svg(project['sheets'][0],svg,1,1)
            export_project_pdf(project,pdf)
            self.assertIn('<svg',svg.read_text(encoding='utf-8'))
            self.assertGreater(pdf.stat().st_size,1000)

    @unittest.skipUnless(quality_render.AVAILABLE,'Pillow no disponible')
    def test_smooth_renderer_has_opaque_component_boxes(self):
        shapes=[
            ('line',10,10,100,60),
            ('polygon',[(25,20),(80,20),(80,55),(25,55)]),
            ('circle',40,40,5),
            ('dot',60,40,4),
        ]
        result=quality_render.symbol_bitmap(shapes,.65)
        self.assertIsNotNone(result)
        image,_,_=result
        self.assertEqual(image.mode,'RGBA')
        pixels=(image.get_flattened_data() if hasattr(image,'get_flattened_data')
                else image.getdata())
        self.assertTrue(any(p[3] and p[0] > 240 for p in pixels))


if __name__=='__main__':
    unittest.main()
