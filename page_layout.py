"""Marco de hoja y cuadrícula de referencias, compartidos entre pantalla y SVG.

Diseño físico: DIN A4 apaisado (297 x 210 mm). Las coordenadas históricas
1280 x 900 del editor se conservan para abrir proyectos anteriores sin cambios.
"""
from __future__ import annotations

A4_WIDTH_MM=297
A4_HEIGHT_MM=210
GREEN='#299144'

def paper_height(width=1280):
    return width*A4_HEIGHT_MM/A4_WIDTH_MM

def guide_geometry(width=1280):
    """Geometría de doble marco y zonas A-H, 1-6, en coordenadas del plano.

    Los labels son marcas de localización de zonas, no enlaces entre hojas.
    """
    height=paper_height(width)
    # A4 apaisado: el marco exterior queda a ~8,35 mm del borde físico.
    # Las letras y números permanecen dentro del área imprimible habitual.
    outside=(36,36,width-36,height-36)
    inside=(56,56,width-56,height-56)
    xo,yo,xr,yb=outside
    xi,yi,xe,ye=inside
    strokes=[]
    for i in range(1,8):
        x=xo+(xr-xo)*i/8
        strokes.append((x,yo,x,yi))
        strokes.append((x,ye,x,yb))
    for i in range(1,6):
        y=yi+(ye-yi)*i/6
        strokes.append((xo,y,xi,y))
        strokes.append((xe,y,xr,y))
    labels=[]
    for i,letter in enumerate('ABCDEFGH'):
        x=xo+(xr-xo)*(i+0.5)/8
        labels.extend(((x,(yo+yi)/2,letter),(x,(ye+yb)/2,letter)))
    for i in range(6):
        y=yi+(ye-yi)*(i+0.5)/6
        labels.extend((((xo+xi)/2,y,str(i+1)),((xe+xr)/2,y,str(i+1))))
    return { 'paper':(width,height), 'outer':outside, 'inner':inside,
             'lines':strokes,'labels':labels }

def svg_frame(width=1280):
    from xml.sax.saxutils import escape
    g=guide_geometry(width)
    out=['<g stroke="'+GREEN+'" fill="none" stroke-width="1.35">']
    for x1,y1,x2,y2 in [g['outer'],g['inner']]:
        out.append(f'<rect x="{x1:.3f}" y="{y1:.3f}" width="{x2-x1:.3f}" height="{y2-y1:.3f}"/>')
    for x1,y1,x2,y2 in g['lines']:
        out.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}"/>')
    out.append('</g>')
    out.append('<g font-family="Arial, sans-serif" font-weight="bold" font-size="12" fill="'+GREEN+'" text-anchor="middle" dominant-baseline="middle">')
    for x,y,label in g['labels']:
        out.append(f'<text x="{x:.3f}" y="{y:.3f}">{escape(label)}</text>')
    out.append('</g>')
    return out


def title_block_geometry():
    """Cajetín compacto, casi apoyado en las líneas interior derecha e inferior.

    La separación de 2 unidades deja el borde del cajetín completamente
    dentro del marco verde, sin tapar las zonas A-H y 1-6. Esta geometría
    se comparte entre pantalla, SVG y PDF A4.
    """
    width=1280
    height=paper_height(width)
    inner_margin=56       # coincide con guide_geometry()['inner']
    gap=2                 # distancia mínima que evita superponer trazos
    block_width=450       # tamaño compacto, no el cajetín alargado de 0.38.2
    block_height=50
    right=width-inner_margin-gap
    bottom=height-inner_margin-gap
    left=right-block_width
    top=bottom-block_height
    divider_x=right-108
    header_y=top+20
    return {
        'outer': (left,top,right,bottom),
        'header_y': header_y,
        'divider_x': divider_x,
        'label_x': left+10,
        'page_x': divider_x+10,
        'heading_y': top+8,
        'value_y': header_y+10,
        'title_max_width': (divider_x-left)-22,
        'left_center_x': (left+divider_x)/2,
        'right_center_x': (divider_x+right)/2,
        'header_center_y': (top+header_y)/2,
        'value_center_y': (header_y+bottom)/2,
    }
