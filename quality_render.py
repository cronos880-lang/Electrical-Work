"""Renderizado de pantalla suavizado de las formas vectoriales del editor.

El motor geométrico y los PDF/SVG siguen siendo vectoriales; este módulo
únicamente mejora el antialiasing en pantallas de zoom reducido. Pillow es
opcional: cuando no está instalado la interfaz usa el Canvas clásico.
"""
from __future__ import annotations
import math

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

SS = 4


def _font(size, supersample=SS, bold=False, family=None):
    # No se distribuyen fuentes con el programa: usa las del equipo.
    names = []
    if family:
        names.append(str(family))
    if bold:
        names += ['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
    else:
        names += ['C:/Windows/Fonts/segoeui.ttf', 'C:/Windows/Fonts/arial.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    names += ['DejaVuSans.ttf', 'Arial.ttf']
    for name in names:
        try:
            return ImageFont.truetype(name, max(1,int(round(size*supersample))))
        except (OSError,ValueError):
            continue
    return ImageFont.load_default(size=max(1,int(round(size*supersample))))


def _color(value):
    from PIL import ImageColor
    try:
        return ImageColor.getrgb(value)
    except (TypeError, ValueError):
        return (32,50,72)


def _dashed(draw, a, b, ink, width, dash=5*SS, gap=3*SS):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    if not length:return
    x,y=dx/length,dy/length
    p=0.0
    while p<length:
        q=min(length,p+dash)
        draw.line((a[0]+x*p,a[1]+y*p,a[0]+x*q,a[1]+y*q),fill=ink,width=width)
        p=q+gap


def symbol_bitmap(shapes, zoom, ink='#21364c', stroke=1.55):
    """Return (PIL RGBA, left, top), rasterizing lines at 4x resolution."""
    if not AVAILABLE or not shapes:return None
    # Bound vector primitives (including symbol-specific glyphs).
    bounds=[]
    for shape in shapes:
        typ=shape[0]
        if typ in ('line','dashline'):
            bounds += [(shape[1],shape[2]),(shape[3],shape[4])]
        elif typ in ('polygon','filledpolygon'):
            bounds += list(shape[1])
        elif typ in ('circle','dot'):
            x,y,r=shape[1:4];bounds += [(x-r,y-r),(x+r,y+r)]
        elif typ in ('text','textend','textcenter'):
            x,y=shape[1:3]
            size=shape[4];approx=max(12,len(str(shape[3]))*size*.7)
            bounds += [(x-approx,y-size),(x+approx,y+size)]
    if not bounds:return None
    xs=[p[0]*zoom for p in bounds];ys=[p[1]*zoom for p in bounds]
    left=math.floor(min(xs)-5);top=math.floor(min(ys)-5)
    right=math.ceil(max(xs)+5);bottom=math.ceil(max(ys)+5)
    w=max(1,right-left);h=max(1,bottom-top)
    # Protect against too-large image layers on malformed elements.
    if w*h>3_500_000:return None
    image=Image.new('RGBA',(w*SS,h*SS),(0,0,0,0))
    draw=ImageDraw.Draw(image)
    linecolor=(*_color(ink),255)
    thickness=max(2,round(stroke*zoom*SS))
    def coord(x,y):return ((x*zoom-left)*SS,(y*zoom-top)*SS)
    for shape in shapes:
        typ=shape[0]
        if typ in ('line','dashline'):
            a=coord(*shape[1:3]);b=coord(*shape[3:5])
            if typ=='dashline':_dashed(draw,a,b,linecolor,thickness)
            else:draw.line((*a,*b),fill=linecolor,width=thickness,joint='curve')
        elif typ in ('polygon','filledpolygon'):
            pts=[coord(*point) for point in shape[1]]
            if typ=='filledpolygon':
                draw.polygon(pts,fill=linecolor)
            else:
                # Unfilled CAD polygons have a transparent inside.
                draw.line(pts+[pts[0]],fill=linecolor,width=thickness,joint='curve')
        elif typ in ('circle','dot'):
            x,y,r=shape[1:4];cx,cy=coord(x,y);radius=r*zoom*SS
            b=(cx-radius,cy-radius,cx+radius,cy+radius)
            draw.ellipse(b,fill=linecolor if typ=='dot' else None,
                         outline=None if typ=='dot' else linecolor,width=thickness)
        elif typ in ('text','textcenter','textend'):
            _,x,y,label,size,color,*family=shape
            xx,yy=coord(x,y)
            alignment={'text':'lm','textcenter':'mm','textend':'rm'}[typ]
            draw.text((xx,yy),str(label),font=_font(size*zoom,family=family[0] if family else None),
                      fill=(*_color(color),255),anchor=alignment)
    return image.resize((w,h),Image.Resampling.LANCZOS),left,top


def label_bitmap(shape, zoom):
    """Return high-quality raster text and its top-left offset from anchor."""
    if not AVAILABLE:return None
    typ,x,y,label,size,color,*family=shape
    if not label:return None
    # Size in the source is a page-space unit. Avoid Canvas's 8pt text floor.
    font=_font(size*zoom,family=family[0] if family else None)
    anchor={'text':'lm','textcenter':'mm','textend':'rm'}[typ]
    check=Image.new('RGBA',(2,2))
    d=ImageDraw.Draw(check)
    bounds=d.textbbox((0,0),str(label),font=font,anchor=anchor)
    x1,y1,x2,y2=bounds
    pad=3*SS
    w=max(2,int(x2-x1+2*pad));h=max(2,int(y2-y1+2*pad))
    img=Image.new('RGBA',(w,h),(0,0,0,0))
    d=ImageDraw.Draw(img)
    d.text((-x1+pad,-y1+pad),str(label),font=font,
           fill=(*_color(color),255),anchor=anchor)
    small=img.resize((max(1,math.ceil(w/SS)),max(1,math.ceil(h/SS))),Image.Resampling.LANCZOS)
    left=x*zoom + (x1-pad)/SS
    top=y*zoom + (y1-pad)/SS
    return small,left,top


def to_tk(bitmap):
    if not AVAILABLE:return None
    return ImageTk.PhotoImage(bitmap)
