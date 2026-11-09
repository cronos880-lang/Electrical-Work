"""Exportación PDF vectorial A4 apaisado sin dependencias obligatorias.

Usa fuentes PDF estándar para texto latino y geometría propia del editor.
Si el plano incluye imágenes, usa Pillow para incrustarlas en el PDF.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
import base64
import zlib
import math

from core import PAGE_W, validate_project, symbol_shapes, junction_points
from page_layout import paper_height, guide_geometry, GREEN, title_block_geometry
from documentation import documentation_rows

A4_WIDTH_PT=297*72/25.4
A4_HEIGHT_PT=210*72/25.4
PAGE_H=paper_height(PAGE_W)
INK='#17324b'
MUTED='#65798b'


def _color(value):
    value=value.lstrip('#')
    return ' '.join(f'{int(value[i:i+2],16)/255:.3f}' for i in (0,2,4))


def _pdf_string(value):
    # Standard PDF Helvetica + WinAnsiEncoding. Mantiene acentos españoles.
    raw=str(value).replace('\r',' ').replace('\n',' ').encode('cp1252','replace')
    return b'('+raw.replace(b'\\',b'\\\\').replace(b'(',b'\\(').replace(b')',b'\\)')+b')'


def _text_width(text,size,bold=False):
    # Anchura tipográfica aproximada suficiente para centrar etiquetas cortas.
    narrow=' ilI.,;:!|\'`'
    wide='MW@%ÑÁÓÚ'# mayúsculas anchas
    total=0
    for c in str(text):
        if c in narrow:total+=.26
        elif c in wide:total+=.82
        elif c.isupper():total+=.64
        elif c.isdigit():total+=.56
        else:total+=.53
    return total*size*(1.035 if bold else 1)


class PDFPage:
    def __init__(self):
        self.ops=[]
        self.images=[]
        self.ops.append(f'q {A4_WIDTH_PT/PAGE_W:.8f} 0 0 {-A4_HEIGHT_PT/PAGE_H:.8f} 0 {A4_HEIGHT_PT:.8f} cm')

    def add(self,value):self.ops.append(value)
    def line(self,x1,y1,x2,y2,color=INK,width=2,dash=False):
        self.add('q')
        self.add(f'{_color(color)} RG {width:g} w '+('[6 4] 0 d ' if dash else '')+
                 f'{x1:.3f} {y1:.3f} m {x2:.3f} {y2:.3f} l S')
        self.add('Q')
    def rect(self,x1,y1,x2,y2,color=INK,width=1.2,fill=None):
        self.add('q')
        self.add(f'{_color(color)} RG {width:g} w')
        if fill:self.add(f'{_color(fill)} rg')
        self.add(f'{x1:.3f} {y1:.3f} {x2-x1:.3f} {y2-y1:.3f} re '+('B' if fill else 'S'))
        self.add('Q')
    def poly(self,pts,color=INK,width=2,fill=None):
        if not pts:return
        self.add('q')
        self.add(f'{_color(color)} RG {width:g} w')
        if fill:self.add(f'{_color(fill)} rg')
        x,y=pts[0]
        parts=[f'{x:.3f} {y:.3f} m']
        parts += [f'{a:.3f} {b:.3f} l' for a,b in pts[1:]]
        parts.append('h '+('B' if fill else 'S'))
        self.add(' '.join(parts))
        self.add('Q')
    def circle(self,cx,cy,r,color=INK,width=2,fill=None):
        k=.55228474983*r
        parts=[f'{cx+r:.3f} {cy:.3f} m',
               f'{cx+r:.3f} {cy+k:.3f} {cx+k:.3f} {cy+r:.3f} {cx:.3f} {cy+r:.3f} c',
               f'{cx-k:.3f} {cy+r:.3f} {cx-r:.3f} {cy+k:.3f} {cx-r:.3f} {cy:.3f} c',
               f'{cx-r:.3f} {cy-k:.3f} {cx-k:.3f} {cy-r:.3f} {cx:.3f} {cy-r:.3f} c',
               f'{cx+k:.3f} {cy-r:.3f} {cx+r:.3f} {cy-k:.3f} {cx+r:.3f} {cy:.3f} c']
        self.add('q')
        self.add(f'{_color(color)} RG {width:g} w')
        if fill:self.add(f'{_color(fill)} rg')
        self.add(' '.join(parts)+' '+('B' if fill else 'S'))
        self.add('Q')
    def text(self,x,y,value,size=12,color=INK,bold=False,align='left',family='Arial'):
        value=str(value)
        if not value:return
        if align=='center':x-=_text_width(value,size,bold)/2
        if align=='right':x-=_text_width(value,size,bold)
        family=(family or 'Arial').casefold()
        code=('F2' if bold else 'F3' if any(n in family for n in ('times','georgia'))
              else 'F4' if any(n in family for n in ('courier','consolas','mono')) else 'F1')
        # CTM anterior invierte Y: esta matriz devuelve el texto al sentido normal.
        self.add('q')
        self.add(f'{_color(color)} rg')
        self.ops.append(b'BT /'+code.encode()+f' {size:.3f} Tf 1 0 0 -1 {x:.3f} {y+size*.35:.3f} Tm '.encode()+_pdf_string(value)+b' Tj ET')
        self.add('Q')
    def image(self,item):
        try:
            from PIL import Image
        except ImportError as e:
            raise RuntimeError('Para exportar planos que contienen imágenes, instala Pillow: py -m pip install Pillow') from e
        raw=base64.b64decode(item['image_data'],validate=True)
        with Image.open(BytesIO(raw)) as picture:
            if picture.width*picture.height>25000000:
                raise ValueError('Imagen demasiado grande para la exportación PDF.')
            picture.load()
            if picture.mode not in ('RGB','L'):
                if 'A' in picture.getbands():
                    layer=Image.new('RGB',picture.size,'white')
                    layer.paste(picture,mask=picture.getchannel('A'))
                    picture=layer
                else:picture=picture.convert('RGB')
            if picture.mode=='L':picture=picture.convert('RGB')
            out=BytesIO();picture.save(out,'JPEG',quality=91,optimize=True)
            w,h=picture.size
            data=out.getvalue()
        image_name='Im'+str(len(self.images)+1)
        self.images.append((image_name,w,h,data))
        dw,dh=item['width'],item['height']
        x,y=item['x']-dw/2,item['y']-dh/2
        self.add('q')
        self.add(f'{dw:.3f} 0 0 {-dh:.3f} {x:.3f} {y+dh:.3f} cm /{image_name} Do')
        self.add('Q')
    def content(self):
        blobs=[]
        for part in self.ops:
            blobs.append(part if isinstance(part,bytes) else part.encode('ascii'))
        blobs.append(b'Q')
        return b'\n'.join(blobs)+b'\n'


class PDFWriter:
    def __init__(self):self.pages=[]
    def add_page(self,page):self.pages.append(page)
    def save(self,path):
        objects=[]
        def obj(data):
            objects.append(data)
            return len(objects)
        def stream(header,data):
            compressed=zlib.compress(data,6)
            return header+f' /Filter /FlateDecode /Length {len(compressed)} >>\nstream\n'.encode()+compressed+b'\nendstream'
        catalog=obj(b'')
        pages_tree=obj(b'')
        font_reg=obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
        font_bold=obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>')
        font_times=obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>')
        font_mono=obj(b'<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>')
        page_ids=[]
        for page in self.pages:
            image_refs=[]
            for name,w,h,data in page.images:
                ref=obj(b'<< /Type /XObject /Subtype /Image /ColorSpace /DeviceRGB '
                        +f'/Width {w} /Height {h} /BitsPerComponent 8 /Filter /DCTDecode /Length {len(data)} >>\nstream\n'.encode()+data+b'\nendstream')
                image_refs.append((name,ref))
            content_id=obj(stream(b'<<',page.content()))
            img_ref=b' '.join(f'/{name} {ref} 0 R'.encode() for name,ref in image_refs)
            resource=(b'<< /Font << /F1 '+str(font_reg).encode()+b' 0 R /F2 '+
                      str(font_bold).encode()+b' 0 R /F3 '+str(font_times).encode()+
                      b' 0 R /F4 '+str(font_mono).encode()+b' 0 R >>')
            if image_refs:resource+=b' /XObject << '+img_ref+b' >>'
            resource+=b' >>'
            page_id=obj(b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 '+
                        f'{A4_WIDTH_PT:.4f} {A4_HEIGHT_PT:.4f}'.encode()+b'] /Resources '+resource+
                        b' /Contents '+f'{content_id} 0 R'.encode()+b' >>')
            page_ids.append(page_id)
        objects[catalog-1]=b'<< /Type /Catalog /Pages 2 0 R >>'
        objects[pages_tree-1]=(b'<< /Type /Pages /Count '+str(len(page_ids)).encode()+b' /Kids ['+
                              b' '.join(f'{p} 0 R'.encode() for p in page_ids)+b'] >>')
        output=bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        positions=[0]
        for ident,record in enumerate(objects,1):
            positions.append(len(output))
            output+=f'{ident} 0 obj\n'.encode()+record+b'\nendobj\n'
        start=len(output)
        output+=f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode()
        for offset in positions[1:]:output+=f'{offset:010d} 00000 n \n'.encode()
        output+=(b'trailer\n<< /Size '+str(len(objects)+1).encode()+
                 b' /Root 1 0 R >>\nstartxref\n'+str(start).encode()+b'\n%%EOF\n')
        Path(path).write_bytes(output)
        return len(self.pages)


def _sheet_page(doc,sheet_number,total):
    page=PDFPage()
    stroke=1.45 if doc.get('drawing_scale',1.0)==0.70 else 2.0
    dot_radius=3 if stroke<2 else 4
    geo=guide_geometry(PAGE_W)
    for bounds in (geo['outer'],geo['inner']):page.rect(*bounds,GREEN,1.35)
    for a,b,c,d in geo['lines']:page.line(a,b,c,d,GREEN,1.35)
    for x,y,label in geo['labels']:page.text(x,y,label,12,GREEN,True,'center')
    for element in doc['elements']:
        if element['kind']=='image':page.image(element)
    for wire in doc['wires']:
        for (x1,y1),(x2,y2) in zip(wire['points'],wire['points'][1:]):
            page.line(x1,y1,x2,y2,INK,stroke)
    for element in doc['elements']:
        for shape in symbol_shapes(element):
            typ=shape[0]
            if typ in ('line','dashline'):
                page.line(*shape[1:5],INK,stroke,typ=='dashline')
            elif typ in ('polygon','filledpolygon'):
                page.poly(shape[1],INK,stroke,INK if typ=='filledpolygon' else None)
            elif typ in ('circle','dot'):
                page.circle(shape[1],shape[2],shape[3],INK,stroke,INK if typ=='dot' else None)
            elif typ in ('text','textcenter','textend'):
                _,x,y,value,size,color,*rest=shape
                page.text(x,y,value,size,color,False,
                          'center' if typ=='textcenter' else 'right' if typ=='textend' else 'left',
                          rest[0] if rest else 'Arial')
    for x,y in junction_points(doc):page.circle(x,y,dot_radius,INK,1,INK)
    # Cajetín compacto compartido con el editor y SVG.
    border='#9fbbca'
    box=title_block_geometry()
    left,top,right,bottom=box['outer']
    page.rect(left,top,right,bottom,border,1)
    page.line(left,box['header_y'],right,box['header_y'],border,1)
    page.line(box['divider_x'],top,box['divider_x'],bottom,border,1)
    page.text(box['left_center_x'],box['header_center_y'],'ELECTRICAL WORK  ·  TÍTULO DEL PLANO',10,MUTED,align='center')
    title=doc['title']
    sz=15
    while _text_width(title,sz)>box['title_max_width'] and sz>9:sz-=1
    page.text(box['left_center_x'],box['value_center_y'],title,sz,INK,bold=False,align='center')
    page.text(box['right_center_x'],box['header_center_y'],'HOJA',10,MUTED,align='center')
    page.text(box['right_center_x'],box['value_center_y'],f'{sheet_number}/{total}',13,INK,align='center')
    return page


def _wrap_text(text,maxwidth,size):
    words=str(text).split(' ')
    lines=[];current=''
    for word in words:
        guess=(current+' '+word).strip()
        if _text_width(guess,size)<maxwidth:
            current=guess
        else:
            if current:lines.append(current)
            if _text_width(word,size)>maxwidth:
                temp=''
                for letter in word:
                    if _text_width(temp+letter,size)>maxwidth and temp:
                        lines.append(temp);temp=letter
                    else:temp+=letter
                current=temp
            else:current=word
    if current:lines.append(current)
    return lines or ['']


def _table_pages(project):
    rows=documentation_rows(project)
    pages=[]
    page=None
    y=0
    page_number=0
    def header():
        nonlocal page,y,page_number
        page_number+=1
        page=PDFPage()
        pages.append(page)
        page.text(50,60,'DOCUMENTACIÓN DEL ESQUEMA',26,INK,True)
        page.text(50,93,project['title'],17,MUTED)
        page.text(1230,93,f'{len(rows)} referencias',13,MUTED,False,'right')
        page.rect(44,119,1236,156,INK,1,INK)
        for col,label in ((58,'FAMILIA'),(310,'REFERENCIA'),(495,'DESCRIPCIÓN'),(1147,'HOJA')):
            page.text(col,139,label,14,'#ffffff',True)
        y=159
    header()
    for index,row in enumerate(rows):
        desc_lines=_wrap_text(row['description'],630,13)
        row_height=max(38,16+len(desc_lines)*17)
        if y+row_height>PAGE_H-60:
            page.text(1230,PAGE_H-43,f'Página {page_number}',12,MUTED,False,'right')
            header()
        page.rect(44,y,1236,y+row_height, '#e4ebf0',.45,
                  '#f4f8fa' if index%2==0 else '#ffffff')
        page.text(58,y+19,row['group'],12,INK)
        page.text(310,y+19,row['reference'],14,INK,True)
        for i,part in enumerate(desc_lines):page.text(495,y+19+i*17,part,13,INK)
        page.text(1147,y+19,row['sheets'],13,MUTED)
        y+=row_height
    if not rows:page.text(66,y+35,'Este proyecto todavía no tiene elementos documentables.',16,MUTED)
    page.text(1230,PAGE_H-43,f'Página {page_number}',12,MUTED,False,'right')
    return pages


def export_project_pdf(project,path,sheet_indices=None,include_documentation=False,documentation_only=False):
    """A4 PDF: una hoja, todas, o sólo/además la documentación."""
    validate_project(project)
    total=len(project['sheets'])
    if sheet_indices is None:sheet_indices=list(range(total))
    if any(not isinstance(i,int) or not 0<=i<total for i in sheet_indices):
        raise ValueError('Número de hoja inválido.')
    doc=PDFWriter()
    if not documentation_only:
        for idx in sheet_indices:
            doc.add_page(_sheet_page(project['sheets'][idx],idx+1,total))
    if include_documentation or documentation_only:
        for page in _table_pages(project):doc.add_page(page)
    if not doc.pages:raise ValueError('No hay páginas para exportar.')
    return doc.save(path)
