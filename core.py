"""Electrical Work - motor de dibujo y formato de documentos (sin simulación)."""
from __future__ import annotations
import html
import base64
import binascii
import json
import math
import uuid
from copy import deepcopy
from pathlib import Path
from xml.sax.saxutils import escape
from page_layout import paper_height,svg_frame,title_block_geometry

LEGACY_FORMAT = 'electrical-work'
LEGACY_COMPACT_FORMAT = 'electrical-work-compact'
FORMAT = 'electrical-work-compact-v2'
FILE_VERSION = 1
PAGE_W, PAGE_H = 1280, 900
GRID = 10
# New designs use a physical 70% symbol geometry; old files retain 100%.
COMPACT_SCALE = 0.70
SUPPORTED_DRAW_SCALES = (1.0, COMPACT_SCALE)
# A strict 70% horizontal reduction makes the contact poles too close for
# readable L1/L2/L3/N references. Keep a minimum 20-unit pitch for multipoles.
MIN_PITCH_KINDS = frozenset({
    'contactor_3p','thermal_3p','breaker_3p','motor_protector_3p',
    'breaker_2p','differential_2p','differential_4p',
    'pushbutton_double','motor_3ph','motor_1ph',
})


def _lateral_scale(item):
    if item.get('compact_geometry',1)<2:return COMPACT_SCALE
    kind=item['kind']
    if kind=='breaker_4p':return 0.5  # 120 -> 60 units; four poles at 20.
    if kind in MIN_PITCH_KINDS:return 1.0
    return COMPACT_SCALE


SYMBOL_NAMES = {
    'contact_no': 'Contacto NA', 'contact_nc': 'Contacto NC',
    'switch_horizontal_no': 'Interruptor · contacto abierto (horizontal)',
    'switch_horizontal_nc': 'Interruptor · contacto cerrado (horizontal)',
    'pushbutton_horizontal_no': 'Pulsador · contacto abierto (horizontal)',
    'pushbutton_horizontal_nc': 'Pulsador · contacto cerrado (horizontal)',
    # Tipos legados: se cargan, editan, dibujan y exportan, aunque no estén en el catálogo.
    'changeover_2pos': 'Conmutador de dos posiciones (proyecto antiguo)',
    'changeover_multi': 'Conmutador multiposiciones (proyecto antiguo)',
    'selector_multi': 'Selector configurable (2–12 posiciones)',
    'switch_double_horizontal': 'Interruptor de contacto doble',
    'coil': 'Bobina', 'pushbutton': 'Pulsador NA', 'pushbutton_nc': 'Pulsador NC',
    'pushbutton_double': 'Pulsador doble NA + NC', 'lamp': 'Lámpara',
    'terminal': 'Borne', 'junction': 'Unión',
    # Biblioteca de automatismos: geometría vectorial original y convencional.
    'contact_timer_no': 'Contacto NA temporizado',
    'contact_timer_nc': 'Contacto NC temporizado',
    'thermal_nc': 'Contacto térmico NC (95-96)',
    'thermal_no': 'Contacto térmico NA (97-98)',
    'limit_no': 'Final de carrera NA',
    'limit_nc': 'Final de carrera NC',
    'coil_contactor': 'Bobina de contactor',
    'coil_timer_on': 'Bobina de temporizador a conexión',
    'coil_timer_off': 'Bobina de temporizador a desconexión',
    'coil_solenoid': 'Bobina de electroválvula',
    'emergency_nc': 'Paro de emergencia NC',
    'selector_no': 'Selector mantenido NA',
    'selector_nc': 'Selector mantenido NC',
    'fuse': 'Fusible',
    'disconnect_1p': 'Seccionador unipolar',
    'breaker_1p': 'Interruptor automático unipolar',
    'thermal_3p': 'Relé térmico tripolar',
    'contactor_3p': 'Contactos de potencia tripolares',
    'motor_1ph': 'Motor monofásico',
    'motor_3ph': 'Motor trifásico',
    'buzzer': 'Zumbador',
    'voltmeter': 'Voltímetro',
    'ammeter': 'Amperímetro',
    'ground': 'Tierra de protección',
    'plc_input': 'Señal PLC: entrada digital',
    'plc_output': 'Señal PLC: salida digital',
    'power_supply': 'Fuente de alimentación AC/DC',
    'plc_module': 'PLC configurable: entradas, salidas y alimentación',
    'breaker_2p': 'Automático 2 polos',
    'breaker_3p': 'Automático 3 polos',
    'breaker_4p': 'Automático 4 polos',
    'differential_2p': 'Diferencial 2 polos',
    'differential_4p': 'Diferencial 4 polos',
    'motor_protector_3p': 'Guardamotor',
    'directional_terminal': 'Borne direccional · Salida',
    'directional_terminal_in': 'Borne direccional · Entrada',
    'pressostat': 'Presostato',
    'vacuostat': 'Vacuostato',
    'thermostat': 'Termostato',
    'sensor_inductive_no': 'Sensor inductivo NA',
    'sensor_inductive_nc': 'Sensor inductivo NC',
    'sensor_capacitive_no': 'Sensor capacitivo NA',
    'sensor_capacitive_nc': 'Sensor capacitivo NC',
    'sensor_magnetic_no': 'Sensor magnético NA',
    'sensor_magnetic_nc': 'Sensor magnético NC',
    'photoelectric_barrier': 'Barrera fotoeléctrica',
}

# Se muestra numeración SOLO en aparatos de contacto y SOLO si se escribe.
CONTACT_TERMINAL_KINDS = frozenset({
    'contact_no','contact_nc','contact_timer_no','contact_timer_nc',
    'switch_horizontal_no','switch_horizontal_nc','pushbutton_horizontal_no','pushbutton_horizontal_nc',
    'changeover_2pos','changeover_multi','switch_double_horizontal','selector_multi',
    'thermal_no','thermal_nc','limit_no','limit_nc',
    'selector_no','selector_nc','pushbutton','pushbutton_nc',
    'pushbutton_double','emergency_nc','contactor_3p','thermal_3p',
    'breaker_2p','breaker_3p','breaker_4p','differential_2p','differential_4p','motor_protector_3p',
    'pressostat','vacuostat','thermostat',
    'sensor_inductive_no','sensor_inductive_nc','sensor_capacitive_no','sensor_capacitive_nc',
    'sensor_magnetic_no','sensor_magnetic_nc','photoelectric_barrier',
    'coil','coil_contactor','coil_timer_on','coil_timer_off','coil_solenoid',
})


def terminal_label_names(item):
    """Los nombres siguen el orden de port_positions; no presupone bornas."""
    kind=item['kind']
    if kind not in CONTACT_TERMINAL_KINDS: return []
    if kind=='pushbutton_double':
        return ['NA superior','NC superior','NA inferior','NC inferior']
    if kind in ('switch_horizontal_no','switch_horizontal_nc',
                'pushbutton_horizontal_no','pushbutton_horizontal_nc'):
        return ['Contacto izquierdo','Contacto derecho']
    if kind=='changeover_2pos':
        return ['Común','Posición superior','Posición inferior']
    if kind=='changeover_multi':
        return ['Contacto 1','Contacto 2','Contacto 3','Contacto 4','Común']
    if kind=='selector_multi':
        count=_check_selector_positions(item.get('selector_positions'))
        return [f'Posición {i+1}' for i in range(count)] + ['Común']
    if kind=='switch_double_horizontal':
        return ['Superior izquierdo','Superior derecho','Inferior izquierdo','Inferior derecho']
    if kind in ('coil','coil_contactor','coil_timer_on','coil_timer_off','coil_solenoid'):
        return ['Borne superior (A1)','Borne inferior (A2)']
    if kind in ('contactor_3p','thermal_3p','breaker_3p','motor_protector_3p'):
        return [f'Polo {i} superior' for i in (1,2,3)]+[f'Polo {i} inferior' for i in (1,2,3)]
    if kind in ('breaker_2p','differential_2p'):
        return ['Polo 1 superior','Polo 2 superior','Polo 1 inferior','Polo 2 inferior']
    if kind in ('differential_4p','breaker_4p'):
        return [f'Polo {i} superior' for i in (1,2,3,4)]+[f'Polo {i} inferior' for i in (1,2,3,4)]
    if kind=='photoelectric_barrier':
        return ['Borne 1','Borne 2','Borne 3','Borne 4','Borne 5']
    return ['Borne superior','Borne inferior']


def get_terminal_labels(item):
    """Anotación opcional; proyectos anteriores no llevan terminal_labels."""
    names=terminal_label_names(item)
    values=item.get('terminal_labels',[])
    return list(values) if isinstance(values,list) and len(values)==len(names) else ['']*len(names)


def annotation_positions(item):
    """Anotaciones de un elemento para dibujar y desplazar independientemente.

    Claves estables por función y borne. Los offsets viven en coordenadas
    locales, de modo que rotar el elemento también rota sus anotaciones.
    No alteran nunca la posición real de los puertos eléctricos.
    """
    kind=item['kind']
    if kind in ('text','image'):return []
    scale=float(item.get('draw_scale',1.0))
    if scale!=1.0:
        original=dict(item);original.pop('draw_scale',None)
        old=annotation_positions(original)
        offsets=item.get('annotation_offsets') or {}
        # Draw compact texts a little smaller, but keep real print height near
        # 2 mm, independently of the zoom.  Multi-pole labels must not overlap.
        adjusted=[(k,_scale_annotation_shape(item,shape,scale)) for k,shape in old]
        if kind in ('plc_input','plc_output') and item.get('compact_geometry',1)>=2:
            # Situar I0.0 / Q0.0 dentro de la banda de cabecera compacta y
            # DI/DO en el centro del cuerpo. El offset manual se conserva.
            corrected=[]
            for key,shape in adjusted:
                if key in ('address','signal'):
                    _,_,_,value,sz,color,*rest=shape
                    off=offsets.get(key,[0,0])
                    if not (isinstance(off,(tuple,list)) and len(off)==2):off=[0,0]
                    dx,dy=_rotate(off[0]*scale, off[1]*scale,item.get('rotation',0))
                    ax,ay=_rotate(0,-15 if key=='address' else 10,item.get('rotation',0))
                    shape=('textcenter',round(item['x']+ax+dx,3),round(item['y']+ay+dy,3),
                           value,10 if key=='address' else 12,color,*rest)
                corrected.append((key,shape))
            return corrected
        return _compact_annotation_layout(item,adjusted,offsets)
    x,y=item['x'],item['y']
    ang=item.get('rotation',0)
    offsets=item.get('annotation_offsets',{})
    if not isinstance(offsets,dict):offsets={}
    result=[]
    def emit(key,typ,px,py,value,size=12):
        if value is None or value=='':return
        off=offsets.get(key,[0,0])
        if not (isinstance(off,(list,tuple)) and len(off)==2):off=(0,0)
        odx,ody=_rotate(off[0],off[1],ang)
        result.append((key,(typ,px+odx,py+ody,str(value),size,'#1c3145')))
    def pos(a,b):
        dx,dy=_rotate(a,b,ang)
        return x+dx,y+dy

    if kind=='plc_module':
        geo=plc_geometry(item)
        top,bottom=geo['top'],geo['bottom']
        for index,(xx,label) in enumerate(((geo['positive'][0],'24v'),(geo['negative'][0],'0v'))):
            emit(f'power:{index}','textcenter',*pos(xx,top+16),label,12)
        for index,xx in enumerate(geo['inputs']):
            emit(f'input:{index}','textcenter',*pos(xx,top+30),plc_channel_name('I',index),10)
        for index,xx in enumerate(geo['outputs']):
            emit(f'output:{index}','textcenter',*pos(xx,bottom-18),plc_channel_name('Q',index),10)
        return result

    if kind in ('directional_terminal','directional_terminal_in'):
        inbound=kind=='directional_terminal_in'
        emit('page','text' if inbound else 'textend',*pos(-38 if inbound else 38,-20),item.get('direction_page',''),12)
        emit('reference','text' if inbound else 'textend',*pos(-44 if inbound else 44,23),item.get('label',''),12)
        return result

    # Horizontal contact families: individual labels just outside their own ports.
    # They rotate with the symbol and can also be freely dragged by the user.
    if kind in ('switch_horizontal_no','switch_horizontal_nc',
                'pushbutton_horizontal_no','pushbutton_horizontal_nc',
                'changeover_2pos','changeover_multi','switch_double_horizontal'):
        places={
            'switch_horizontal_no':[(-60,-16),(60,-16)],
            'switch_horizontal_nc':[(-60,-16),(60,-16)],
            'pushbutton_horizontal_no':[(-60,-16),(60,-16)],
            'pushbutton_horizontal_nc':[(-60,-16),(60,-16)],
            'changeover_2pos':[(-60,-16),(60,-34),(60,6)],
            'changeover_multi':[(-47,-40),(-7,-40),(33,-40),(73,-40),(16,43)],
            'switch_double_horizontal':[(-60,-36),(60,-36),(-60,4),(60,4)],
        }[kind]
        for index,value in enumerate(get_terminal_labels(item)):
            if value:
                emit(f'terminal:{index}','textcenter',*pos(*places[index]),value,11)
        if item.get('label'):
            emit('reference','textend',*pos(-100 if kind=='changeover_multi' else -67,
                                           -94 if kind=='changeover_multi' else -50),item['label'],13)
        return result

    if kind=='selector_multi':
        # Cada contacto tiene una posición individual de rótulo, incluso
        # después de girar el componente.
        contacts=selector_fixed_x(item['selector_positions'])
        for index,value in enumerate(get_terminal_labels(item)):
            if not value:continue
            local=(contacts[index],-76) if index<len(contacts) else (0,76)
            emit(f'terminal:{index}','textcenter',*pos(*local),value,11)
        if item.get('label'):
            emit('reference','textend',*pos(contacts[0]-28,-10),item['label'],13)
        return result

    ports=port_positions(item)
    for index,value in enumerate(get_terminal_labels(item)):
        if not value or index>=len(ports):continue
        px,py=ports[index]
        ox,oy=_rotate(14,-16 if index>=len(ports)//2 else 16,ang)
        emit(f'terminal:{index}','text',px+ox,py+oy,value,11)

    if kind in ('plc_input','plc_output'):
        emit('address','textcenter',*pos(0,-34),item.get('label',''),12)
        emit('signal','textcenter',*pos(0,19),item.get('signal_type',''),18)
        return result

    if item.get('label') and kind!='junction':
        if kind in CONTACT_TERMINAL_KINDS:
            distance=(122 if kind=='breaker_4p' else 66 if kind.startswith(('limit_','thermal_','selector_','contact_timer_')) or kind in ('pushbutton','pushbutton_nc','pushbutton_double','emergency_nc','pressostat','vacuostat','thermostat','sensor_inductive_no','sensor_inductive_nc','sensor_capacitive_no','sensor_capacitive_nc','sensor_magnetic_no','sensor_magnetic_nc','photoelectric_barrier') else 58 if kind in ('contactor_3p','breaker_3p','breaker_4p','motor_protector_3p','differential_4p') else 44 if kind in ('breaker_2p','differential_2p') else 34)
            emit('reference','textend',x-distance,y-8,item['label'],13)
        else:
            distance=72 if kind=='power_supply' else 62 if kind=='coil_solenoid' else 36 if kind in ('motor_1ph','motor_3ph') else 27
            emit('reference','text',x+distance,y-8,item['label'],13)
    return result


DEFAULT_REFS = {
    'contact_no':'S', 'contact_nc':'S', 'coil':'K',
    'switch_horizontal_no':'S','switch_horizontal_nc':'S',
    'pushbutton_horizontal_no':'S','pushbutton_horizontal_nc':'S',
    'changeover_2pos':'S','changeover_multi':'S','selector_multi':'S',
    'switch_double_horizontal':'S',
    'pushbutton':'S', 'pushbutton_nc':'S', 'pushbutton_double':'S', 'lamp':'H', 'terminal':'X', 'junction':'',
    'contact_timer_no':'K','contact_timer_nc':'K','thermal_nc':'F','thermal_no':'F',
    'limit_no':'S','limit_nc':'S','coil_contactor':'KM','coil_timer_on':'KT',
    'coil_timer_off':'KT','coil_solenoid':'Y','emergency_nc':'S',
    'selector_no':'S','selector_nc':'S','fuse':'F','disconnect_1p':'Q',
    'breaker_1p':'Q','thermal_3p':'F','contactor_3p':'KM',
    'motor_1ph':'M','motor_3ph':'M','buzzer':'H','voltmeter':'P',
    'ammeter':'P','ground':'PE',
    'plc_input':'','plc_output':'','power_supply':'G','plc_module':'PLC',
    'breaker_2p':'F','breaker_3p':'F','breaker_4p':'F','differential_2p':'F','differential_4p':'F',
    'motor_protector_3p':'Q','directional_terminal':'X','directional_terminal_in':'X',
    'pressostat':'B','vacuostat':'B','thermostat':'B',
    'sensor_inductive_no':'B','sensor_inductive_nc':'B','sensor_capacitive_no':'B','sensor_capacitive_nc':'B',
    'sensor_magnetic_no':'B','sensor_magnetic_nc':'B','photoelectric_barrier':'B',
}



def snap(n, grid=GRID):
    return round(float(n)/grid)*grid


def new_id():
    return uuid.uuid4().hex[:12]


def new_document():
    return {'format': FORMAT, 'version': FILE_VERSION, 'title': 'Esquema sin título',
            'elements': [], 'wires': [], 'drawing_scale': COMPACT_SCALE,
            'page': {'width': PAGE_W, 'height': PAGE_H}}


def make_symbol(kind, x, y, label=None, rotation=0, plc_inputs=8, plc_outputs=8,
                selector_positions=3, draw_scale=1.0):
    if kind not in SYMBOL_NAMES:
        raise ValueError(f'Símbolo desconocido: {kind}')
    if float(draw_scale) not in SUPPORTED_DRAW_SCALES:
        raise ValueError('Escala de símbolo no permitida.')
    item={'id':new_id(), 'kind':kind, 'x':snap(x), 'y':snap(y),
          'rotation':int(rotation)%360,'label':label or ''}
    if draw_scale != 1.0:
        item['draw_scale']=float(draw_scale)
        item['compact_geometry']=2  # V0.1 projects keep original port positions.
    if kind in ('directional_terminal','directional_terminal_in'):
        item.update(direction_page='')
    if kind=='selector_multi':
        _check_selector_positions(selector_positions)
        item['selector_positions']=selector_positions
    if kind=='plc_module':
        _check_plc_counts(plc_inputs,plc_outputs)
        item.update(plc_inputs=plc_inputs,plc_outputs=plc_outputs,
                    label=label or '',
                    plc_brand='',
                    plc_model='')
    # Campo de descripción de señal independiente de la dirección (I0.0/Q0.0).
    if kind in ('plc_input','plc_output'):
        item['label']=label if label else ('I0.0' if kind=='plc_input' else 'Q0.0')
        item['signal_type']='DI' if kind=='plc_input' else 'DO'
    return item



MAX_PLC_CHANNELS = 24
MAX_SELECTOR_POSITIONS = 12
MIN_SELECTOR_POSITIONS = 2


def _check_selector_positions(count):
    if type(count) is not int or not MIN_SELECTOR_POSITIONS <= count <= MAX_SELECTOR_POSITIONS:
        raise ValueError('El selector admite entre 2 y 12 posiciones enteras.')
    return count


def selector_fixed_x(count):
    _check_selector_positions(count)
    return [-(count-1)*20 + index*40 for index in range(count)]



def _check_plc_counts(inputs,outputs):
    if type(inputs) is not int or type(outputs) is not int:
        raise ValueError('Las cantidades de entradas y salidas deben ser enteras.')
    if not (0<=inputs<=MAX_PLC_CHANNELS and 0<=outputs<=MAX_PLC_CHANNELS and inputs+outputs>0):
        raise ValueError(f'Indica entre 0 y {MAX_PLC_CHANNELS} entradas/salidas, con al menos una señal.')


def plc_geometry(item):
    """Coordenadas de dibujo y bornes alineadas con la rejilla de 20.

    Evita separaciones entre cables ajustados a la rejilla y los trazos
    de entrada, salida y alimentación del PLC.
    """
    ni, no = item['plc_inputs'], item['plc_outputs']
    _check_plc_counts(ni, no)
    # El ancho es múltiplo de 40, los bordes quedan sobre la rejilla.
    width = max(400, 160 + 40 * max(ni, no))
    half = width // 2
    top, bottom = -140, 140
    inputs = [-half + 140 + index * 40 for index in range(ni)]
    outputs = [-(no - 1) * 20 + index * 40 for index in range(no)]
    return {
        'left': -half, 'right': half,
        'top': top, 'bottom': bottom,
        'inputs': inputs, 'outputs': outputs,
        'input_port_y': top - 20, 'output_port_y': bottom + 20,
        'positive': (-half + 20, top - 20),
        'negative': (-half + 60, top - 20),
        'brand_box': (-72, -24, 72, 8),
        'model_box': (-72, 40, 72, 72),
    }


def plc_channel_name(prefix,number):
    # Numeración sucesiva: I0.0–I0.7, I1.0..., y Q equivalentes.
    return f'{prefix}{number//8}.{number%8}'


def make_text(x,y,text='Texto',font_family='Arial',font_size=14):
    if not isinstance(font_family,str) or not (1<=len(font_family)<=60):
        raise ValueError('Fuente no válida.')
    if type(font_size) is not int or not 8<=font_size<=72:
        raise ValueError('El tamaño debe estar entre 8 y 72.')
    return {'id':new_id(),'kind':'text','x':snap(x),'y':snap(y),
            'rotation':0,'label':text,'font_family':font_family,'font_size':font_size}


def make_image(x,y,encoded,format,width,height):
    item={'id':new_id(),'kind':'image','x':snap(x),'y':snap(y),
          'rotation':0,'label':'','image_data':encoded,'image_format':format,
          'width':int(width),'height':int(height)}
    _validate_image(item)
    return item


def _validate_image(item):
    if item.get('image_format') not in ('png','gif','jpeg'):
        raise ValueError('Formato de imagen no compatible.')
    if any(type(item.get(k)) is not int or not (1<=item[k]<=2000) for k in ('width','height')):
        raise ValueError('Tamaño de imagen no válido.')
    raw=item.get('image_data')
    if not isinstance(raw,str) or len(raw)>6000000 or not raw:
        raise ValueError('Datos de imagen no válidos.')
    try:binary=base64.b64decode(raw,validate=True)
    except (ValueError,binascii.Error):raise ValueError('Imagen codificada no válida.')
    if len(binary)>4500000:raise ValueError('Imagen demasiado grande.')
    fmt=item['image_format']
    signatures={'png': binary.startswith(b'\x89PNG\r\n\x1a\n'),
                'gif':binary.startswith((b'GIF87a',b'GIF89a')),
                'jpeg':binary.startswith(b'\xff\xd8\xff')}
    if not signatures[fmt]:raise ValueError('El contenido no corresponde al formato de imagen.')
    return item


def _clean_points(points):
    result=[]
    for p in points:
        p=[int(p[0]), int(p[1])]
        if not result or result[-1]!=p:
            result.append(p)
    return result


def make_wire(start, end, horizontal_first=True):
    x1,y1=map(lambda v:int(snap(v)), start)
    x2,y2=map(lambda v:int(snap(v)), end)
    if x1==x2 or y1==y2:
        points=[[x1,y1],[x2,y2]]
    elif horizontal_first:
        points=[[x1,y1],[x2,y1],[x2,y2]]
    else:
        points=[[x1,y1],[x1,y2],[x2,y2]]
    points=_clean_points(points)
    if len(points)<2:
        raise ValueError('El cable debe tener una longitud mayor que cero')
    return {'id':new_id(), 'points':points}



def move_wire(doc, wire_id, dx, dy):
    """Desplaza un cable completo, sin alterar su forma, sobre la rejilla.

    Retorna el desplazamiento realmente aplicado. Respeta los límites de
    edición y conserva tramos rectos, codos y rectángulos cerrados.
    Trasladar un cable por separado desconecta sus extremos de los símbolos
    que no se muevan con él.
    """
    wire=next((w for w in doc['wires'] if w['id']==wire_id),None)
    if wire is None:
        raise ValueError('Cable no encontrado.')
    points=wire['points']
    if not points:
        return 0,0
    xs=[p[0] for p in points];ys=[p[1] for p in points]
    dx=int(snap(dx));dy=int(snap(dy))
    dx=max(GRID-min(xs), min(PAGE_W-GRID-max(xs), dx))
    dy=max(GRID-min(ys), min(PAGE_H-GRID-max(ys), dy))
    dx=int(snap(dx));dy=int(snap(dy))
    if dx or dy:
        wire['points']=[[x+dx,y+dy] for x,y in points]
    return dx,dy


def make_straight_wire(start, end):
    """Línea de dos puntos sin obligación de orientación ortogonal."""
    a=[int(snap(v)) for v in start]
    b=[int(snap(v)) for v in end]
    if a==b:raise ValueError('La línea recta debe tener longitud positiva')
    return {'id':new_id(),'points':[a,b],'mode':'straight'}


def make_rectangle_wire(start, end):
    """Rectángulo/cuadrado cerrado en la rejilla, tratado como trazo único."""
    x1,y1=[int(snap(v)) for v in start]
    x2,y2=[int(snap(v)) for v in end]
    if x1==x2 or y1==y2:
        raise ValueError('El cuadrado/rectángulo debe tener ancho y alto')
    return {'id':new_id(),'points':[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]],
            'mode':'rectangle'}


def _dist2(p, q):
    return (p[0]-q[0])**2+(p[1]-q[1])**2


def point_on_segment(point, first, second, strict=False):
    """Punto sobre un segmento horizontal/vertical (sin aproximaciones)."""
    x,y=point
    x1,y1=first
    x2,y2=second
    if x1==x2==x:
        low,high=sorted((y1,y2))
        return low<y<high if strict else low<=y<=high
    if y1==y2==y:
        low,high=sorted((x1,x2))
        return low<x<high if strict else low<=x<=high
    # Segmentos oblicuos admitidos para el modo de línea recta.
    dx=x2-x1;dy=y2-y1
    cross=(x-x1)*dy-(y-y1)*dx
    if abs(cross)>1e-6:return False
    dot=(x-x1)*dx+(y-y1)*dy
    extent=dx*dx+dy*dy
    return 0<dot<extent if strict else 0<=dot<=extent



def wire_connection_target(doc, x, y, tolerance=14):
    """Busca el terminal o punto de cable existente bajo el cursor.

    Devuelve {'point':(x,y),'kind':'port'|'wire_end'|'wire_segment',
              'owner':id} o None. Las coordenadas de la conexión se
    ajustan a la rejilla, sin desplazar los cables existentes.
    Los puertos de símbolos tienen prioridad cuando se solapan.
    """
    if tolerance<=0:return None
    candidates=[]
    for item in doc['elements']:
        for point in port_positions(item):
            d2=_dist2(point,(x,y))
            if d2<=tolerance*tolerance:
                candidates.append((0,d2,{'point':point,'kind':'port','owner':item['id']}))
    for wire in doc['wires']:
        pts=wire['points']
        for p in (pts[0],pts[-1]):
            q=tuple(p)
            d2=_dist2(q,(x,y))
            if d2<=tolerance*tolerance:
                candidates.append((1,d2,{'point':q,'kind':'wire_end','owner':wire['id']}))
        for a,b in zip(pts,pts[1:]):
            if a[0]==b[0]:
                projection=(a[0],max(min(a[1],b[1]),min(max(a[1],b[1]),snap(y))))
            elif a[1]==b[1]:
                projection=(max(min(a[0],b[0]),min(max(a[0],b[0]),snap(x))),a[1])
            else:
                # Para una recta diagonal, conexiones solo en puntos reales
                # de su segmento que también pertenezcan a la rejilla.
                # Evita crear una falsa unión fuera de la propia línea.
                steps=math.gcd(abs(int(b[0]-a[0])),abs(int(b[1]-a[1])))//GRID
                if not steps:continue
                projection=min(
                    ((a[0]+(b[0]-a[0])*i/steps,
                      a[1]+(b[1]-a[1])*i/steps) for i in range(steps+1)),
                    key=lambda p:_dist2(p,(x,y)))
            d2=_dist2(projection,(x,y))
            if d2<=tolerance*tolerance:
                candidates.append((2,d2,{'point':projection,'kind':'wire_segment','owner':wire['id']}))
    if not candidates:return None
    return min(candidates,key=lambda c:(c[0],c[1]))[2]


def junction_points(doc):
    """Puntos de unión visual de un cable con otro.

    T: un extremo termina sobre el interior de otro cable => punto.
    Cruce X de dos segmentos por su interior => SIN punto automático.
    Dos extremos unidos en línea => SIN punto; tres => punto.
    """
    endpoints={}
    for wire in doc['wires']:
        for endpoint in (tuple(wire['points'][0]),tuple(wire['points'][-1])):
            endpoints.setdefault(endpoint,set()).add(wire['id'])
    result=set()
    for point,owners in endpoints.items():
        if len(owners)>=3:
            result.add(point)
            continue
        for wire in doc['wires']:
            if wire['id'] in owners:continue
            if any(point_on_segment(point,a,b,strict=True)
                   for a,b in zip(wire['points'],wire['points'][1:])):
                result.add(point)
                break
    return sorted(result)


def _rotate(x,y,degrees):
    # Sólo rotaciones ortogonales: no genera desviaciones de rejilla.
    a=degrees%360
    if a==0:return x,y
    if a==90:return -y,x
    if a==180:return -x,-y
    if a==270:return y,-x
    raise ValueError('La rotación debe ser múltiplo de 90°')


def port_positions(item):
    if item['kind'] in ('text','image'): return []
    kind=item['kind']
    if kind in ('terminal','junction'):
        local=[(0,0)]
    elif kind=='ground':
        local=[(0,-40)]
    elif kind in ('switch_horizontal_no','switch_horizontal_nc',
                  'pushbutton_horizontal_no','pushbutton_horizontal_nc'):
        local=[(-60,0),(60,0)]
    elif kind=='changeover_2pos':
        local=[(-60,0),(60,-20),(60,20)]
    elif kind=='changeover_multi':
        local=[(-60,-60),(-20,-60),(20,-60),(60,-60),(0,60)]
    elif kind=='selector_multi':
        local=[(xx,-60) for xx in selector_fixed_x(item['selector_positions'])]+[(0,60)]
    elif kind=='switch_double_horizontal':
        local=[(-60,-20),(60,-20),(-60,20),(60,20)]
    elif kind=='pushbutton_double':
        local=[(-20,-40),(20,-40),(-20,40),(20,40)]
    elif kind in ('thermal_3p','contactor_3p','breaker_3p','motor_protector_3p'):
        local=[(-20,-40),(0,-40),(20,-40),(-20,40),(0,40),(20,40)]
    elif kind in ('breaker_2p','differential_2p'):
        local=[(-10,-40),(10,-40),(-10,40),(10,40)]
    elif kind=='differential_4p':
        local=[(-30,-40),(-10,-40),(10,-40),(30,-40),(-30,40),(-10,40),(10,40),(30,40)]
    elif kind=='breaker_4p':
        # Cuatro polos a rejilla de 20: extremos reales para conectar cables.
        local=[(-60,-40),(-20,-40),(20,-40),(60,-40),
               (-60,40),(-20,40),(20,40),(60,40)]
    elif kind=='motor_3ph':
        local=[(-20,-40),(0,-40),(20,-40)]
    elif kind=='motor_1ph':
        local=[(-20,-40),(20,-40)]
    elif kind=='plc_input':
        local=[(0,-60)]
    elif kind=='plc_output':
        local=[(0,60)]
    elif kind=='plc_module':
        geo=plc_geometry(item)
        local=[(x,geo['input_port_y']) for x in geo['inputs']]
        local += [(x,geo['output_port_y']) for x in geo['outputs']]
        local += [geo['positive'],geo['negative']]
    elif kind=='power_supply':
        local=[(-60,-20),(-60,20),(60,-20),(60,20)]
    elif kind=='directional_terminal':
        local=[(-40,0)]
    elif kind=='directional_terminal_in':
        local=[(40,0)]
    elif kind=='photoelectric_barrier':
        local=[(-12,-40),(12,-40),(-18,40),(0,40),(18,40)]
    else:
        local=[(0,-40),(0,40)]
    scale=float(item.get('draw_scale',1.0))
    if scale not in SUPPORTED_DRAW_SCALES:
        raise ValueError('Escala del elemento no admitida.')
    # For compact items snap each rotated local port to the 10-unit drawing grid.
    # A drawn line and its wire endpoint must land on precisely the same coordinate.
    if scale!=1.0 and item.get('compact_geometry',1)<2:
        return [(int(item['x']+snap(_rotate(a,b,item.get('rotation',0))[0]*scale)),
                 int(item['y']+snap(_rotate(a,b,item.get('rotation',0))[1]*scale))) for a,b in local]
    if scale!=1.0:
        lateral=_lateral_scale(item)
        return [(int(item['x']+_rotate(snap(a*lateral),snap(b*scale),item.get('rotation',0))[0]),
                 int(item['y']+_rotate(snap(a*lateral),snap(b*scale),item.get('rotation',0))[1]))
                for a,b in local]
    return [(int(item['x']+_rotate(a,b,item.get('rotation',0))[0]),
             int(item['y']+_rotate(a,b,item.get('rotation',0))[1])) for a,b in local]


def _retarget_wire_endpoint(points, idx, new):
    """Mantiene cables a 90° al desplazar/rotar su puerto de conexión.

    Inserta un codo cuando un cable inicialmente recto deja de serlo.
    """
    old=points[idx][:]
    new=list(new)
    if old==new:return
    if len(points)==2:
        other=points[1-idx][:]
        if new[0]==other[0] or new[1]==other[1]:
            points[idx]=new
        elif old[0]==other[0]:  # antes era vertical
            # Mantener cerca del otro extremo la orientación previa.
            if idx==0:
                points[:]=[new,[other[0],new[1]],other]
            else:
                points[:]=[other,[other[0],new[1]],new]
        else:  # antes era horizontal
            if idx==0:
                points[:]=[new,[new[0],other[1]],other]
            else:
                points[:]=[other,[new[0],other[1]],new]
    else:
        adj=1 if idx==0 else idx-1
        if points[adj][0]==old[0]:points[adj][0]=new[0]
        elif points[adj][1]==old[1]:points[adj][1]=new[1]
        points[idx]=new
    # Retira vértices repetidos. Un cable de longitud cero nunca es válido.
    cleaned=_clean_points(points)
    if len(cleaned)>=2:points[:]=cleaned


def _update_wires_at_ports(doc,old_ports,new_ports):
    """Update original wire endpoints exactly once on move or rotation.

    Never iterate live coordinates over all poles: a new port can coincide
    with the OLD location of the adjacent pole (especially after rotation),
    which previously caused the same cable to be displaced repeatedly.
    """
    mapping=dict(zip(old_ports,new_ports))
    for wire in doc['wires']:
        pts=wire['points']
        original=((tuple(pts[0]),0),(tuple(pts[-1]),-1))
        changes=[(idx,mapping[old]) for old,idx in original if old in mapping and old!=mapping[old]]
        # End then start: _retarget_wire_endpoint may create extra corners.
        for idx,point in changes[::-1]:
            if wire.get('mode')=='straight':
                wire['points'][idx]=list(point)
            elif wire.get('mode')=='rectangle':
                continue
            else:
                target=0 if idx==0 else len(wire['points'])-1
                _retarget_wire_endpoint(wire['points'],target,point)


def move_element(doc, item_id, x, y):
    """Mueve símbolo y actualiza extremos de cables unidos a sus bornes."""
    item=next(e for e in doc['elements'] if e['id']==item_id)
    old_ports=port_positions(item)
    item['x'],item['y']=snap(x),snap(y)
    _update_wires_at_ports(doc,old_ports,port_positions(item))


def rotate_element(doc, item_id, direction=1):
    item=next(e for e in doc['elements'] if e['id']==item_id)
    old_ports=port_positions(item)
    item['rotation']=(item.get('rotation',0)+90*direction)%360
    _update_wires_at_ports(doc,old_ports,port_positions(item))

def validate_document(obj):
    if not isinstance(obj,dict) or obj.get('format') not in (FORMAT,LEGACY_FORMAT,LEGACY_COMPACT_FORMAT):
        raise ValueError('El archivo no es un proyecto Electrical Work.')
    if obj.get('version')!=FILE_VERSION:
        raise ValueError('Versión de proyecto incompatible.')
    if not isinstance(obj.get('title'),str) or len(obj['title'])>200:
        raise ValueError('Título inválido.')
    if float(obj.get('drawing_scale',1.0)) not in SUPPORTED_DRAW_SCALES:
        raise ValueError('Escala de hoja incompatible.')
    page=obj.get('page',{})
    if not isinstance(page,dict) or page.get('width')!=PAGE_W or page.get('height')!=PAGE_H:
        raise ValueError('Tamaño de hoja no compatible en esta versión.')
    for key in ('elements','wires'):
        if not isinstance(obj.get(key),list) or len(obj[key])>10000:
            raise ValueError('Estructura del proyecto inválida.')
    ids=set()
    for item in obj['elements']:
        if not isinstance(item,dict) or item.get('kind') not in set(SYMBOL_NAMES)|{'text','image'}:
            raise ValueError('Elemento no reconocido.')
        if not isinstance(item.get('label'),str) or len(item['label'])>240:
            raise ValueError('Etiqueta inválida.')
        if float(item.get('draw_scale',1.0)) not in SUPPORTED_DRAW_SCALES:
            raise ValueError('Escala de elemento inválida.')
        if item['kind']=='text':
            family=item.get('font_family','Arial')
            sz=item.get('font_size',14)
            if not isinstance(family,str) or not (1<=len(family)<=60) or any(ord(c)<32 for c in family):
                raise ValueError('Fuente del texto inválida.')
            if type(sz) is not int or not (8<=sz<=72):
                raise ValueError('Tamaño del texto inválido.')
        if item['kind']=='image':_validate_image(item)
        if item['kind']=='selector_multi':
            _check_selector_positions(item.get('selector_positions'))
        if item['kind']=='plc_module':
            _check_plc_counts(item.get('plc_inputs'),item.get('plc_outputs'))
            for key in ('plc_brand','plc_model'):
                value=item.get(key,'')
                if not isinstance(value,str) or len(value)>120 or any(ord(c)<32 for c in value):
                    raise ValueError('Texto de PLC inválido.')
        if item['kind'] in ('directional_terminal','directional_terminal_in'):
            # Aceptar direction_text de proyectos anteriores, pero no dibujarlo.
            for key,limit in (('direction_page',80),('direction_text',160)):
                content=item.get(key,'')
                if not isinstance(content,str) or len(content)>limit or any(ord(ch)<32 for ch in content):
                    raise ValueError('Texto o dirección de página inválidos.')
        if item['kind'] in ('plc_input','plc_output'):
            desc=item.get('signal_type','DI' if item['kind']=='plc_input' else 'DO')
            if not isinstance(desc,str) or len(desc)>32 or any(ord(c)<32 for c in desc):
                raise ValueError('Descripción de señal PLC inválida.')
        if item.get('rotation') not in (0,90,180,270):
            raise ValueError('Rotación inválida.')
        if 'terminal_labels' in item:
            labels=item['terminal_labels']
            if item['kind'] not in CONTACT_TERMINAL_KINDS or not isinstance(labels,list) or len(labels)!=len(terminal_label_names(item)):
                raise ValueError('Lista de números de contacto inválida.')
            if any(not isinstance(number,str) or len(number)>12 or '\n' in number or '\r' in number for number in labels):
                raise ValueError('Número de contacto inválido.')
        if 'annotation_offsets' in item:
            offsets=item['annotation_offsets']
            kind=item['kind']
            allowed={'reference'} if kind not in ('text','image','plc_module') else set()
            if kind in CONTACT_TERMINAL_KINDS:
                allowed.update(f'terminal:{j}' for j in range(len(terminal_label_names(item))))
            if kind=='plc_module':
                allowed.update(('power:0','power:1'))
                allowed.update(f'input:{j}' for j in range(MAX_PLC_CHANNELS))
                allowed.update(f'output:{j}' for j in range(MAX_PLC_CHANNELS))
            if kind in ('directional_terminal','directional_terminal_in'):
                allowed.add('page')
            if kind in ('plc_input','plc_output'):
                allowed.update(('address','signal'))
            if not isinstance(offsets,dict) or len(offsets)>256:
                raise ValueError('Posiciones de numeración inválidas.')
            for key,point in offsets.items():
                if (not isinstance(key,str) or key not in allowed or
                    not isinstance(point,list) or len(point)!=2 or
                    any(type(value) not in (int,float) or not math.isfinite(value)
                        or abs(value)>3000 for value in point)):
                    raise ValueError('Posición de numeración inválida.')
        for key in ('x','y'):
            if type(item.get(key)) not in (float,int) or not math.isfinite(item[key]) or abs(item[key])>100000:
                raise ValueError('Coordenadas inválidas.')
        _validate_id(item,ids)
    for wire in obj['wires']:
        if not isinstance(wire,dict): raise ValueError('Cable inválido.')
        _validate_id(wire,ids)
        mode=wire.get('mode','orthogonal')
        if mode not in ('orthogonal','straight','rectangle'):
            raise ValueError('Modalidad de línea desconocida.')
        points=wire.get('points')
        if not isinstance(points,list) or len(points)<2 or len(points)>10000:
            raise ValueError('Puntos de cable inválidos.')
        for p in points:
            if not isinstance(p,list) or len(p)!=2 or any(type(c) not in (int,float) or not math.isfinite(c) or abs(c)>100000 for c in p):
                raise ValueError('Coordenadas de cable inválidas.')
        for a,b in zip(points,points[1:]):
            if a==b or (mode!='straight' and a[0]!=b[0] and a[1]!=b[1]):
                raise ValueError('Un cable debe tener segmentos rectos y ortogonales.')
        if mode=='straight' and len(points)!=2:
            raise ValueError('Una línea recta debe tener dos puntos.')
        if mode=='rectangle':
            if len(points)!=5 or points[0]!=points[-1]:
                raise ValueError('El rectángulo debe ser una figura cerrada.')
            x1,y1=points[0];x2,y2=points[2]
            if x1==x2 or y1==y2 or points!=[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]]:
                raise ValueError('El rectángulo es inválido.')
    return obj


def _validate_id(item, ids):
    ident=item.get('id')
    if not isinstance(ident,str) or not ident or len(ident)>64 or ident in ids:
        raise ValueError('Identificador vacío o duplicado.')
    ids.add(ident)


def save_document(doc, path):
    doc=deepcopy(doc)
    doc['format']=FORMAT
    validate_document(doc)
    dst=Path(path)
    payload=json.dumps(doc,indent=2,ensure_ascii=False)+'\n'
    # Guardado atómico para no sobrescribir con un documento parcial.
    import os, tempfile
    fd,name=tempfile.mkstemp(prefix='.ew-',suffix='.tmp',dir=str(dst.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name,dst)
    finally:
        if os.path.exists(name): os.unlink(name)


def load_document(path):
    """Abre hojas V1, y también proyectos V2 de una única hoja.

    Un proyecto con varias hojas debe abrirse con load_project para no
    descartar silenciosamente el resto de sus páginas.
    """
    with open(path,'r',encoding='utf-8') as file:
        obj=json.load(file)
    if isinstance(obj,dict) and obj.get('version')==PROJECT_VERSION:
        validate_project(obj)
        if len(obj['sheets'])!=1:
            raise ValueError('El proyecto contiene varias hojas: utiliza load_project.')
        return deepcopy(obj['sheets'][0])
    return deepcopy(validate_document(obj))


def _shape(kind):
    """Biblioteca vectorial actualizada en V0.35 sin elementos gráficos propietarios."""
    from symbology import symbol_primitives
    return symbol_primitives(kind)


def _compact_point(item, x, y, old_ports, new_ports, scale):
    if item.get('compact_geometry',1)<2:
        # Preserve pixel-for-pixel V0.1 geometry and its connected cables.
        x_axis={orig[0]:port[0] for orig,port in zip(old_ports,new_ports)}
        y_axis={orig[1]:port[1] for orig,port in zip(old_ports,new_ports)}
        xx=next((newx for oldx,newx in x_axis.items() if abs(x-oldx)<1e-7),None)
        yy=next((newy for oldy,newy in y_axis.items() if abs(y-oldy)<1e-7),None)
        return (xx if xx is not None else round(item['x']+(x-item['x'])*scale,3),
                yy if yy is not None else round(item['y']+(y-item['y'])*scale,3))
    # Scale in the component's LOCAL coordinates, not along the screen axes.
    # This preserves every contact's vertical stem through 90° rotations.
    angle=item.get('rotation',0)
    ux,uy=_rotate(x-item['x'],y-item['y'],-angle)
    sx,sy=_rotate(ux*_lateral_scale(item),uy*scale,angle)
    px,py=item['x']+sx,item['y']+sy
    for (ax,ay),(bx,by) in zip(old_ports,new_ports):
        if abs(x-ax)<1e-7 and abs(y-ay)<1e-7:
            return (bx,by)
    # Si un conductor sale verticalmente de un borne redondeado a rejilla,
    # toda su recta usa el mismo eje. Sin esto, PLC y sensores de varios
    # bornes mostraban segmentos cortos inclinados junto al contorno.
    x_targets={}
    y_targets={}
    for (ax,ay),(bx,by) in zip(old_ports,new_ports):
        x_targets.setdefault(ax,set()).add(bx)
        y_targets.setdefault(ay,set()).add(by)
    for axis,targets in x_targets.items():
        if abs(x-axis)<1e-7 and len(targets)==1:
            px=next(iter(targets))
            break
    for axis,targets in y_targets.items():
        if abs(y-axis)<1e-7 and len(targets)==1:
            py=next(iter(targets))
            break
    return (round(px,3),round(py,3))


def _compact_shapes(item, shapes):
    """Scale actual symbol geometry, not its canvas zoom or the page frame.

    The source primitives are always kept at high vector fidelity. Terminals
    are snapped to GRID and the same coordinates are returned by port_positions.
    """
    scale=float(item.get('draw_scale',1.0))
    if scale==1.0 or item['kind'] in ('text','image'):return shapes
    raw=dict(item);raw.pop('draw_scale',None)
    old_ports=port_positions(raw)
    new_ports=port_positions(item)
    def pt(a,b):return _compact_point(item,a,b,old_ports,new_ports,scale)
    out=[]
    for shape in shapes:
        typ=shape[0]
        if typ in ('line','dashline'):
            out.append((typ,*pt(shape[1],shape[2]),*pt(shape[3],shape[4])))
        elif typ in ('polygon','filledpolygon'):
            out.append((typ,[pt(x,y) for x,y in shape[1]]))
        elif typ in ('circle','dot'):
            out.append((typ,*pt(shape[1],shape[2]),round(shape[3]*scale,3)))
        elif typ in ('text','textcenter','textend'):
            # Symbol-specific glyphs scale down; numerical annotations are
            # handled separately, with slightly larger typography for print.
            out.append((typ,*pt(shape[1],shape[2]),shape[3],max(8,round(shape[4]*0.82)),*shape[5:]))
        else:out.append(shape)
    return out


# All of these families have several equally spaced, independently wired poles.
# Compacting the contact centres is safe, but their labels need staggering.
COMPACT_MULTIPOLE = frozenset({
    'thermal_3p','contactor_3p','breaker_2p','breaker_3p','breaker_4p',
    'differential_2p','differential_4p','motor_protector_3p',
    'pushbutton_double','switch_double_horizontal',
})


def _compact_annotation_layout(item, annotations, offsets):
    """Rotulación técnica de catálogo compacto para todas las familias.

    - Numeración fuera del cuerpo, hacia el exterior de los bornes.
    - Referencias fuera del perímetro visual (especialmente magnetotérmicos).
    - Aparatos multipolares: filas alternas cuando el texto no cabe.
    - Los desplazamientos hechos a mano siempre prevalecen.

    Esta capa NO toca la geometría de conexión ni el valor de las etiquetas.
    """
    kind=item['kind']
    angle=item.get('rotation',0)
    ports=port_positions(item)
    bykey=dict(annotations)

    def user_offset(key):
        off=offsets.get(key,[0,0])
        if not (isinstance(off,(tuple,list)) and len(off)==2):off=[0,0]
        return _rotate(off[0]*COMPACT_SCALE,off[1]*COMPACT_SCALE,angle)

    # Bornes: se separa el número del cuerpo, no se imprime sobre el hilo.
    # Horizontal/selector configurable mantienen su propio reparto especial.
    custom=('switch_horizontal_no','switch_horizontal_nc',
            'pushbutton_horizontal_no','pushbutton_horizontal_nc',
            'changeover_2pos','changeover_multi',
            'switch_double_horizontal','selector_multi')
    if kind not in COMPACT_MULTIPOLE and kind not in custom:
        for i,(px,py) in enumerate(ports):
            key=f'terminal:{i}'
            if key not in bykey:continue
            typ,_,_,value,size,color,*rest=bykey[key]
            ux,uy=_rotate(px-item['x'],py-item['y'],-angle)
            if abs(uy)>=abs(ux) or kind.startswith('motor_'):
                # Para los motores trifásicos todos los bornes están arriba.
                dy=-7 if uy<0 else 7
                dx=10
            else:
                dx=-10 if ux<0 else 10
                dy=-7
            shiftx,shifty=_rotate(dx,dy,angle)
            offx,offy=user_offset(key)
            bykey[key]=('textcenter',round(px+shiftx+offx,3),
                        round(py+shifty+offy,3),value,size,color,*rest)

    if kind in COMPACT_MULTIPOLE and kind!='switch_double_horizontal':
        count=len(ports)
        half=count//2
        # Barrera fotoeléctrica: 2 entradas superiores y 3 bornes inferiores.
        if kind=='photoelectric_barrier':half=2
        if count>=4 and half>=2:
            for upper in (True,False):
                used=[]
                indices=range(half) if upper else range(half,count)
                for i in indices:
                    key=f'terminal:{i}'
                    if key not in bykey:continue
                    typ,_,_,name,size,color,*rest=bykey[key]
                    px,py=ports[i]
                    rx,ry=_rotate(px-item['x'],py-item['y'],-angle)
                    textwidth=max(8,len(name)*size*.60)
                    left,right=rx-textwidth/2-2,rx+textwidth/2+2
                    row=0
                    while row<len(used) and any(left<b and right>a for a,b in used[row]):
                        row+=1
                    if row==len(used):used.append([])
                    used[row].append((left,right))
                    extra=13+row*13
                    local_y=ry-extra if upper else ry+extra
                    # Los números quedan al lado del conductor, no encima.
                    dx,dy=_rotate(rx+8,local_y,angle)
                    shiftx,shifty=user_offset(key)
                    bykey[key]=('textcenter',round(item['x']+dx+shiftx,3),
                                round(item['y']+dy+shifty,3),name,size,color,*rest)

    # Referencias: apoyar la etiqueta fuera de la silueta real, en lugar
    # de usar una distancia fija que invade disparadores y cuerpos grandes.
    if ('reference' in bykey and 'reference' not in offsets
        and kind not in custom
        and kind not in ('directional_terminal','directional_terminal_in')):
        shapes=symbol_shapes(item,include_annotations=False)
        xx=[]
        for sh in shapes:
            if sh[0] in ('line','dashline'):
                xx.extend((sh[1],sh[3]))
            elif sh[0] in ('polygon','filledpolygon'):
                xx.extend(p[0] for p in sh[1])
            elif sh[0] in ('circle','dot'):
                xx.extend((sh[1]-sh[3],sh[1]+sh[3]))
        if xx:
            typ,_,_,value,size,color,*rest=bykey['reference']
            if typ=='textend':
                ax=min(xx)-8
            elif typ=='text':
                ax=max(xx)+8
            else:
                ax=bykey['reference'][1]
            bykey['reference']=(typ,round(ax,3),
                                round(item['y']-5,3),value,size,color,*rest)
    # Las referencias se desplazan a otra línea cuando coinciden con una
    # numeración, también con el símbolo girado 90/270 grados. No toca las
    # etiquetas posicionadas manualmente por el usuario.
    if 'reference' in bykey and 'reference' not in offsets:
        def bbox(sh):
            anchor,xx,yy,value,size,*_=sh
            width=max(4,len(str(value))*size*.68)
            if anchor=='textend':return (xx-width,yy-size*.54,xx,yy+size*.54)
            if anchor=='textcenter':return (xx-width/2,yy-size*.54,xx+width/2,yy+size*.54)
            return (xx,yy-size*.54,xx+width,yy+size*.54)
        ref=bykey['reference']
        oldy=ref[2]
        obstacles=[bbox(sh) for key,sh in bykey.items() if key!='reference']
        for change in (0,-15,15,-30,30,-45,45):
            candidate=(ref[0],ref[1],oldy+change,*ref[3:])
            a=bbox(candidate)
            if not any(min(a[2],b[2])-max(a[0],b[0])>1 and
                       min(a[3],b[3])-max(a[1],b[1])>1 for b in obstacles):
                bykey['reference']=candidate
                break
    return [(key,bykey[key]) for key,_ in annotations]


def _scale_annotation_shape(item, shape, scale):
    typ,x,y,label,size,color,*rest=shape
    # Printed character height remains legible at 70%, but is no longer
    # disproportionately large next to small technical contacts.
    if size>=17:
        font_size=12
    elif size>=13:
        font_size=10
    else:
        font_size=9
    return (typ,round(item['x']+(x-item['x'])*scale,3),
            round(item['y']+(y-item['y'])*scale,3),label,
            font_size,color,*rest)


def symbol_shapes(item, include_annotations=True):
    """Transforma primitivas geométricas a coordenadas de página.

    Los círculos/rectángulos se representan de forma que las rotaciones
    ortogonales también queden bien dibujadas en SVG.
    """
    if item['kind']=='text':
        return [('text',item['x'],item['y'],item['label'],item.get('font_size',14),'#1c3145',item.get('font_family','Arial'))]
    if item['kind']=='image':return []
    x,y,ang=item['x'],item['y'],item.get('rotation',0)
    def pos(a,b):
        da,db=_rotate(a,b,ang)
        return x+da,y+db
    shapes=[]
    if item['kind']=='plc_module':
        geo=plc_geometry(item)
        left,right,top,bottom=(geo[key] for key in ('left','right','top','bottom'))
        a,b,c,d=pos(left,top),pos(right,top),pos(right,bottom),pos(left,bottom)
        shapes.append(('polygon',[a,b,c,d]))
        def draw_line(p,q):shapes.append(('line',*pos(*p),*pos(*q)))
        def draw_text(p,value,size=12,anchor='textcenter'):
            u,v=pos(*p);shapes.append((anchor,u,v,value,size,'#1c3145'))
        def text_box(bounds,text_value,size=12):
            x1,y1,x2,y2=bounds
            w=max(120, int(len(text_value)*7 + 30))
            cx=(x1+x2)//2; cy=(y1+y2)//2
            x1=cx-w//2; x2=cx+w//2
            draw_line((x1,y1),(x2,y1)); draw_line((x2,y1),(x2,y2)); draw_line((x2,y2),(x1,y2)); draw_line((x1,y2),(x1,y1))
            draw_text((cx,cy),text_value,size)
        for xx in (geo['positive'][0],geo['negative'][0]):
            draw_line((xx,geo['input_port_y']),(xx,top))
        for xx in geo['inputs']:
            draw_line((xx,geo['input_port_y']),(xx,top))
        for xx in geo['outputs']:
            draw_line((xx,bottom),(xx,geo['output_port_y']))
        text_box(geo['brand_box'], item.get('plc_brand','Aqui Marca plc'), 12)
        text_box(geo['model_box'], item.get('plc_model','Modelo del plc'), 12)
        shapes=_compact_shapes(item,shapes)
        if include_annotations:
            shapes.extend(shape for _,shape in annotation_positions(item))
        return shapes
    # Los componentes creados en V0.2 mantienen sus PUERTOS originales;
    # esta revisión solo cambia el aspecto de ciertos cuerpos compactos.
    from symbology import selector_rotary, compact_symbol_primitives
    if item['kind']=='selector_multi':
        primitives=selector_rotary(item['selector_positions'])
    elif (item.get('draw_scale',1.0)!=1.0 and item.get('compact_geometry',1)>=2):
        primitives=compact_symbol_primitives(item['kind'])
    else:
        primitives=_shape(item['kind'])
    for primitive in primitives:
        typ=primitive[0]
        if typ in ('line','dashline'):
            a,b=pos(primitive[1],primitive[2]),pos(primitive[3],primitive[4])
            shapes.append((typ,*a,*b))
        elif typ in ('rect','fillrect'):
            a,b,c,d=primitive[1:]
            p=[pos(a,b),pos(c,b),pos(c,d),pos(a,d)]
            shapes.append(('filledpolygon' if typ=='fillrect' else 'polygon',p))
        elif typ in ('circle','dot'):
            a,b=pos(primitive[1],primitive[2]);shapes.append((typ,a,b,primitive[3]))
        elif typ in ('glyph','mark'):
            a,b=pos(primitive[1],primitive[2])
            shapes.append(('textcenter' if typ=='mark' else 'text',a,b,primitive[3],primitive[4],'#1c3145'))
    shapes=_compact_shapes(item,shapes)
    if include_annotations:
        shapes.extend(shape for _,shape in annotation_positions(item))
    return shapes


def svg_escape(value):
    return escape(str(value),{'"':'&quot;','\'':'&apos;'})


def _svg_shape(shape):
    typ=shape[0]
    if typ in ('line','dashline'):
        _,x1,y1,x2,y2=shape
        dash=' stroke-dasharray="5 4"' if typ=='dashline' else ''
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{dash} />'
    if typ in ('polygon','filledpolygon'):
        fill='#17324b' if typ=='filledpolygon' else 'white'
        return '<polygon points="'+ ' '.join(f'{x},{y}' for x,y in shape[1]) +f'" fill="{fill}" />'
    if typ in ('circle','dot'):
        _,x,y,r=shape
        return f'<circle cx="{x}" cy="{y}" r="{r}"'+(' fill="#17324b"' if typ=='dot' else ' fill="white"')+' />'
    if typ in ('text','textcenter','textend'):
        _,x,y,text,size,color,*family=shape
        font=svg_escape(family[0] if family else 'Arial, sans-serif')
        anch=' text-anchor="middle" dominant-baseline="middle"' if typ=='textcenter' else ' text-anchor="end"' if typ=='textend' else ''
        return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" stroke="none" font-family="{font}"{anch}>{svg_escape(text)}</text>'
    raise ValueError('Primitive not supported')


def export_svg(doc,path,sheet_number=None,sheet_total=None):
    validate_document(doc)
    w,h=PAGE_W,PAGE_H
    if sheet_number is not None and sheet_total is not None:
        if not (1<=sheet_number<=sheet_total<=MAX_SHEETS):
            raise ValueError('Número de hoja inválido al exportar.')
    footer=(f'{sheet_number}/{sheet_total}' if sheet_number is not None and sheet_total is not None else '1/1')
    physical_h=paper_height(w)
    stroke=1.45 if doc.get('drawing_scale',1.0)==COMPACT_SCALE else 2.0
    dot_radius=3 if stroke<2 else 4
    contents=[f'<?xml version="1.0" encoding="UTF-8"?>',
              f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 {w} {physical_h:.5f}">',
              '<rect width="100%" height="100%" fill="white" />']
    contents.extend(svg_frame(w))
    # Imágenes de cada hoja incrustadas en el SVG: sin dependencias externas.
    for el in doc['elements']:
        if el['kind']=='image':
            iw,ih=el['width'],el['height']
            fmt=el['image_format']
            data=el['image_data']
            contents.append(f'<image x="{el["x"]-iw/2:g}" y="{el["y"]-ih/2:g}" width="{iw}" height="{ih}" preserveAspectRatio="none" href="data:image/{fmt};base64,{data}" />')
    contents.append(f'<g stroke="#17324b" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" fill="none">')
    for wire in doc['wires']:
        points=' '.join(f'{x},{y}' for x,y in wire['points'])
        contents.append(f'<polyline points="{points}" />')
    for el in doc['elements']:
        for shape in symbol_shapes(el):
            contents.append(_svg_shape(shape))
    for x,y in junction_points(doc):
        contents.append(f'<circle cx="{x}" cy="{y}" r="{dot_radius}" fill="#17324b" stroke="none" />')
    contents.append('</g>')
    # Cajetín compacto, mismas coordenadas que pantalla y PDF.
    box=title_block_geometry()
    lx,ty,rx,by=box['outer'];split=box['divider_x'];hy=box['header_y']
    title=doc['title']
    title_size=max(9,min(15,int(box['title_max_width']*1.8/max(1,len(title)))))
    contents += ['<g fill="none" stroke="#9fbbca" stroke-width="1">',
                 f'<rect x="{lx}" y="{ty}" width="{rx-lx}" height="{by-ty}" />',
                 f'<line x1="{lx}" y1="{hy}" x2="{rx}" y2="{hy}" />',
                 f'<line x1="{split}" y1="{ty}" x2="{split}" y2="{by}" />',
                 '</g>',
                 f'<text x="{box["left_center_x"]}" y="{box["header_center_y"]}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="10" fill="#64748b">ELECTRICAL WORK · TÍTULO DEL PLANO</text>',
                 f'<text x="{box["left_center_x"]}" y="{box["value_center_y"]+1}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="{title_size}" fill="#17324b">{svg_escape(title)}</text>',
                 f'<text x="{box["right_center_x"]}" y="{box["header_center_y"]}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="10" fill="#64748b">HOJA</text>',
                 f'<text x="{box["right_center_x"]}" y="{box["value_center_y"]+1}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="13" fill="#17324b">{footer}</text>',
                 '</svg>']
    Path(path).write_text('\n'.join(contents),encoding='utf-8')


def make_demo():
    doc=new_document()
    # Historic fixture uses its original port positions and wire coordinates.
    doc['drawing_scale']=1.0
    doc['title']='Ejemplo: mando básico de un relé'
    # Dos ramas; muestra los símbolos, cables ortogonales y etiquetas.
    for kind,x,y,label in [
        ('contact_nc',320,320,'S0 - Paro'),
        ('contact_no',320,500,'S1 - Marcha'),
        ('coil',320,660,'K1'),
        ('contact_no',660,500,'K1 - Auxiliar'),
        ('lamp',900,660,'H1 - Piloto'),
        ('junction',320,400,''),('junction',320,580,'')]:
        doc['elements'].append(make_symbol(kind,x,y,label))
    lines=[((320,160),(320,280)),((320,360),(320,460)),
           ((320,540),(320,620)),((320,700),(320,760)),
           ((320,760),(900,760)),((900,700),(900,760)),
           ((660,460),(660,400)),((660,400),(320,400)),
           ((660,540),(660,580)),((660,580),(320,580)),
           ((900,620),(900,160)),((900,160),(320,160))]
    for a,b in lines: doc['wires'].append(make_wire(a,b))
    return doc


def make_automation_catalog():
    """Proyecto de ejemplo para evaluar la ampliación del catálogo."""
    doc=new_document()
    doc['title']='Biblioteca de automatismos · V0.11'
    kinds=[
        'switch_horizontal_no','switch_horizontal_nc','pushbutton_horizontal_no','pushbutton_horizontal_nc',
        'switch_double_horizontal','selector_multi',
        'contact_no','contact_nc','contact_timer_no','contact_timer_nc','thermal_nc',
        'thermal_no','limit_no','limit_nc','selector_no','selector_nc',
        'coil','coil_contactor','coil_timer_on','coil_timer_off','coil_solenoid',
        'pushbutton','pushbutton_nc','emergency_nc','fuse','breaker_1p',
        'disconnect_1p','breaker_2p','breaker_3p','breaker_4p','differential_2p','differential_4p','motor_protector_3p','thermal_3p','contactor_3p','motor_1ph','motor_3ph',
        'pressostat','vacuostat','thermostat',
        'sensor_inductive_no','sensor_inductive_nc','sensor_capacitive_no','sensor_capacitive_nc',
        'sensor_magnetic_no','sensor_magnetic_nc','photoelectric_barrier','directional_terminal','directional_terminal_in',
        'lamp','buzzer','voltmeter','ammeter','ground',
    ]
    for index,kind in enumerate(kinds):
        col,row=index%5,index//5
        doc['elements'].append(make_symbol(kind,140+col*220,145+row*112,
                                              DEFAULT_REFS[kind]+str(index+1),
                                              draw_scale=doc['drawing_scale']))
    return doc


# Formato de proyecto V2: contiene una o varias hojas V1 completas.
PROJECT_VERSION=2
MAX_SHEETS=1000


def new_project(title='Esquema sin título'):
    doc=new_document()
    doc['title']=title
    return {'format':FORMAT,'version':PROJECT_VERSION,'title':title,'sheets':[doc],'documentation':{}}


def validate_project(project):
    if not isinstance(project,dict) or project.get('format') not in (FORMAT,LEGACY_FORMAT,LEGACY_COMPACT_FORMAT) or project.get('version')!=PROJECT_VERSION:
        raise ValueError('El archivo no es un proyecto de varias hojas Electrical Work.')
    title=project.get('title')
    if not isinstance(title,str) or not title.strip() or len(title)>200:
        raise ValueError('El nombre del proyecto es inválido.')
    sheets=project.get('sheets')
    if not isinstance(sheets,list) or not 1<=len(sheets)<=MAX_SHEETS:
        raise ValueError('El proyecto debe contener entre 1 y 1000 hojas.')
    for doc in sheets:
        validate_document(doc)
    notes=project.get('documentation',{})
    if not isinstance(notes,dict) or len(notes)>12000:
        raise ValueError('Estructura de documentación inválida.')
    for k,v in notes.items():
        if not isinstance(k,str) or len(k)>140 or not isinstance(v,str) or len(v)>600 or '\n' in v or '\r' in v:
            raise ValueError('Entrada de documentación inválida.')
    hidden=project.get('documentation_hidden',[])
    if not isinstance(hidden,list) or len(hidden)>12000 or len(set(hidden))!=len(hidden):
        raise ValueError('Lista de filas ocultas inválida.')
    if any(not isinstance(key,str) or not 1<=len(key)<=140 for key in hidden):
        raise ValueError('Identificador de fila oculta inválido.')
    manual=project.get('documentation_manual',[])
    if not isinstance(manual,list) or len(manual)>12000:
        raise ValueError('Tabla de documentación manual inválida.')
    identifiers=set()
    for row in manual:
        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not 1<=len(row['id'])<=64:
            raise ValueError('Fila manual de documentación inválida.')
        if row['id'] in identifiers:raise ValueError('Identificadores de documentación repetidos.')
        identifiers.add(row['id'])
        group=row.get('group')
        if (not isinstance(group,str) or not group.strip() or len(group)>80
                or any(c in group for c in '\r\n')):
            raise ValueError('Familia de documentación inválida.')
        for key,limit,required in (('reference',100,True),('description',600,False),('sheets',30,False)):
            value=row.get(key,'')
            if not isinstance(value,str) or len(value)>limit or (required and not value.strip()) or any(c in value for c in '\r\n'):
                raise ValueError('Campo de documentación manual inválido.')
    return project


def project_from_document(doc):
    validate_document(doc)
    return {'format':FORMAT,'version':PROJECT_VERSION,'title':doc['title'],'sheets':[deepcopy(doc)],'documentation':{}}


def save_project(project,path):
    # A new identifier prevents V0.1 from silently misreading new geometry.
    project=deepcopy(project)
    project['format']=FORMAT
    for doc in project['sheets']:
        doc['format']=FORMAT
    validate_project(project)
    dst=Path(path)
    payload=json.dumps(project,indent=2,ensure_ascii=False)+'\n'
    import os,tempfile
    fd,tmp=tempfile.mkstemp(prefix='.ew-',suffix='.tmp',dir=str(dst.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(payload);f.flush();os.fsync(f.fileno())
        os.replace(tmp,dst)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def load_project(path):
    with open(path,'r',encoding='utf-8') as f:obj=json.load(f)
    if not isinstance(obj,dict):raise ValueError('Archivo Electrical Work inválido.')
    if obj.get('version')==FILE_VERSION:
        return project_from_document(obj)
    return deepcopy(validate_project(obj))
