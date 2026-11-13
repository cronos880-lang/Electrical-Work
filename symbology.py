"""Electrical Work V0.35: dibujo vectorial de automatismos.

Dibujos originales basados en convenciones de esquemas industriales IEC de
fabricantes (ABB, Siemens) y referencias públicas; NO son facsímiles de la
base IEC 60617, ni están certificados o validados símbolo por símbolo.
Todas las primitivas son líneas/rectángulos/círculos/textos. La geometría
eléctrica coincide con los puertos del motor de dibujo de ±40 unidades.
"""
from __future__ import annotations
import math


def ln(x1,y1,x2,y2):return ('line',x1,y1,x2,y2)
def dl(x1,y1,x2,y2):return ('dashline',x1,y1,x2,y2)
def rc(x1,y1,x2,y2):return ('rect',x1,y1,x2,y2)
def fr(x1,y1,x2,y2):return ('fillrect',x1,y1,x2,y2)
def ci(x,y,r):return ('circle',x,y,r)
def dt(x,y,r):return ('dot',x,y,r)
def tx(x,y,text,size=11):return ('mark',x,y,text,size)


def arcs(cx,cy,rx,ry,start,end,segments=10):
    """Curvas breves construidas con tramos vectoriales (sin bitmaps)."""
    result=[]
    for n in range(segments):
        a=math.radians(start+(end-start)*n/segments)
        b=math.radians(start+(end-start)*(n+1)/segments)
        result.append(ln(round(cx+rx*math.cos(a),2),round(cy+ry*math.sin(a),2),
                         round(cx+rx*math.cos(b),2),round(cy+ry*math.sin(b),2)))
    return result


def leads(t=-18,b=18):return [ln(0,-40,0,t),ln(0,b,0,40)]


def contact(nc=False):
    """Contacto IEC vertical orientado como S1 de la referencia del usuario.

    La pieza fija está arriba y hacia la izquierda; la lámina móvil parte
    del conductor inferior. En NA existe separación visible; en NC hay
    contacto en reposo. Los puntos de conexión continúan en (0, ±40).
    """
    f=leads(-18,18)
    f += [ln(0,-18,-9,-18),ln(0,18,-9,-18 if nc else -8)]
    return f


def push_mark(emergency=False):
    """Accionamiento lateral.

    Para el paro de emergencia se usa el símbolo aportado por el usuario:
    cabeza semicircular a la izquierda y acoplamiento mecánico discontinuo
    hasta el contacto NC.
    """
    if emergency:
        f=[]
        f += arcs(-30,0,7,10,90,270,8)
        f += [dl(-23,0,-8,0)]
        return f
    return [ln(-33,-10,-33,10),ln(-33,-10,-25,-10),ln(-33,0,-25,0),
            ln(-33,10,-25,10),dl(-25,0,-8,0)]
def push_contact(nc=False, x=0):
    """Misma convención NA/NC del pulsador de la imagen de referencia."""
    f=[ln(x,-40,x,-17),ln(x,17,x,40)]
    if nc:
        # El brazo hace contacto con la pieza fija superior en reposo.
        f += [ln(x,-17,x+6,-17),ln(x+6,-17,x,17)]
    else:
        # El brazo inclinado termina libre: abertura visible en arriba.
        f += [ln(x-13,-18,x,17)]
    return f


def push_double():
    """Pulsador combinado NA+NC: dos circuitos, un mando mecánico común."""
    f=[]
    for x,nc in [(-20,False),(20,True)]:
        f.extend(push_contact(nc,x))
    # Mando E y transmisión mecánica de trazo discontinuo, NO conductor.
    f += [ln(-53,-10,-53,10),ln(-53,-10,-46,-10),
          ln(-53,0,-46,0),ln(-53,10,-46,10),dl(-46,0,23,0)]
    return f

def time_mark():
    # Marca de función temporal, no define tiempo ni sentido de retardo.
    return [dl(-10,-5,-18,-5),ln(-21,-15,-21,10),ln(-21,-15,-14,-15),
            ln(-21,10,-14,10),tx(-28,19,'t',10)]


def overload_mark():
    # Marca funcional de disparo térmico; el contacto conserva estado NA/NC.
    return [dl(-8,-3,-16,-3),ln(-26,-12,-18,-12),ln(-18,-12,-18,0),
            ln(-18,0,-26,0),ln(-26,0,-26,11),ln(-26,11,-18,11)]


def roller_mark():
    """Rodillo y varilla perfectamente HORIZONTALES (petición del usuario)."""
    return [dl(-9,-4,-17,-4),ln(-17,-4,-31,-4),ci(-36,-4,5)]

def selector_mark():
    # Selector rotativo mantenido: mando con eje mecánico punteado.
    return [dl(-9,-4,-19,-4),ci(-21,-4,2),ln(-21,-4,-30,-17),
            ln(-30,-17,-24,-24)]


def coil(kind):
    if kind in ('coil_timer_on','coil_timer_off'):
        # Imagen aportada: zona pequeña adosada a la IZQUIERDA del
        # cuerpo rectangular. Retardo a conexión = X; a desconexión
        # = banda negra. Bornes verticales invariantes (0,-40) (0,40).
        f=leads(-16,16)+[rc(-16,-16,19,16)]
        if kind=='coil_timer_on':
            f += [rc(-29,-16,-16,16),ln(-29,-16,-16,16),
                  ln(-29,16,-16,-16)]
        else:
            f += [fr(-29,-16,-16,16)]
        return f
    if kind=='coil_solenoid':
        # Imagen aportada: bobina rectangular con un accionamiento
        # de válvula de doble triángulo a su derecha, unido por vástago.
        f=leads(-16,16)+[rc(-22,-16,15,16),ln(15,0,36,0)]
        # Dos triángulos opuestos con vértice común, tal como la imagen.
        f += [ln(28,-20,44,-20),ln(28,-20,36,0),ln(44,-20,36,0),
              ln(28,20,44,20),ln(28,20,36,0),ln(44,20,36,0),
              ln(36,-26,36,-20),ln(36,20,36,26)]
        return f
    return leads(-17,17)+[rc(-19,-17,19,17)]

def protection(kind):
    if kind=='fuse':
        # Forma de cartucho IEC: rectángulo estrecho atravesado por el hilo.
        return [ln(0,-40,0,-18),rc(-7,-18,7,18),ln(0,-18,0,18),ln(0,18,0,40)]
    if kind=='disconnect_1p':
        # Seccionador: contacto móvil separado de un contacto fijo.
        return [ln(0,-40,0,-17),ln(0,-17,13,9),
                ln(0,17,9,17),ln(0,17,0,40)]
    # Interruptor automático: elemento de corte + representación de disparo;
    # unión mecánica representada mediante rayas, nunca conexión conductora.
    return [ln(0,-40,0,-17),ln(0,-17,13,8),ln(0,17,9,17),ln(0,17,0,40),
            rc(-27,-8,-15,8),dl(-15,0,-1,0),tx(-21,0,'I',9)]


def power(kind):
    f=[]
    if kind=='thermal_3p':
        # Tres elementos de sobrecarga en serie; independientes eléctricamente.
        for x in (-20,0,20):
            f += [ln(x,-40,x,-13),rc(x-6,-13,x+6,13),
                  ln(x-4,-9,x+4,-1),ln(x+4,-1,x-4,7),ln(x-4,7,x+4,11),
                  ln(x,13,x,40)]
        # No se añade barra transversal: podría confundirse con un puente.
        return f
    # Contactor de tres polos: tres contactos de potencia distintos y un
    # acoplamiento mecánico a trazos, no un puente eléctrico entre fases.
    for x in (-20,0,20):
        f += [ln(x,-40,x,-17),ln(x,-17,x+9,8),
              ln(x,17,x+9,17),ln(x,17,x,40),
              dl(x+11,8,x+11,24)]
    f += [dl(-9,26,31,26)]
    return f


def multipole_breaker(poles=2, differential=False, motor=False, aligned_four_pole=False):
    """Símbolos de protección multipolar inspirados en la referencia del usuario."""
    if poles==2: xs=(-10,10)
    elif poles==3: xs=(-20,0,20)
    elif aligned_four_pole: xs=(-60,-20,20,60)
    else: xs=(-30,-10,10,30)
    f=[]
    # Bloque lateral común
    f += [rc(xs[0]-28,-14,xs[0]-10,4), ln(xs[0]-19,-14,xs[0]-19,4), ln(xs[0]-28,-5,xs[0]-10,-5)]
    f += [ln(xs[0]-10,-5,xs[0]-2,-5)]
    if differential or motor:
        f += [tx(xs[0]-15,16,'L',10)]
    for i,x in enumerate(xs):
        f += [ln(x,-40,x,-17), ln(x,-17,x+9,8), ln(x,17,x+9,17), ln(x,17,x,40)]
        if differential:
            if i==0:
                f += [arcs(x-4,20,10,6,180,360,8)[0]]
            f += [ln(x-2,16,x+2,16)]
        if motor:
            f += [rc(x-8,12,x+8,28), tx(x,20,'>',10)]
        elif not differential:
            f += [fr(x-16,-20,x-10,-14)]
    if poles>1:
        f += [dl(xs[0]+11,26,xs[-1]+11,26)]
    return f


def directional_terminal_shape(inbound=False):
    """Borne direccional de salida y de entrada.

    - Salida: la línea termina en una flecha hacia fuera.
    - Entrada: la flecha apunta hacia dentro y la línea continúa después,
      manteniendo el punto de conexión en el extremo derecho.
    """
    if inbound:
        # Flecha de entrada: la flecha apunta hacia dentro (a la derecha)
        # y la línea continúa hacia el interior del esquema.
        return [ln(-40,-9,-24,0), ln(-24,0,-40,9),
                ln(-40,9,-40,-9), ln(-24,0,40,0)]
    return [ln(-40,0,24,0), ln(24,-9,40,0),
            ln(40,0,24,9), ln(24,9,24,-9)]


def contact_ring(x,y):
    """Small unfilled terminal in the supplied reference drawings."""
    return [ci(x,y,4.5)]


def horizontal_switch(nc=False):
    """Reference 1: two-terminal horizontal switch, open or closed."""
    f=[ln(-60,0,-24,0),ln(24,0,60,0)]
    f+=contact_ring(-20,0)+contact_ring(20,0)
    if nc:
        # Closed blade touches both fixed terminals, on the horizontal axis.
        f += [ln(-20,0,20,0)]
    else:
        # Open blade rises at the right and clearly stops before the contact.
        f += [ln(-20,0,13,-16)]
    return f


def horizontal_pushbutton(nc=False):
    """Reference 1: contact pair and T-shaped pushbutton actuator."""
    f=[ln(-60,0,-24,0),ln(24,0,60,0)]
    f+=contact_ring(-20,0)+contact_ring(20,0)
    # Horizontal bridge, with a visible 9-unit gap in the NA form.
    f += [ln(-20,-10,-20,-7),ln(20,-10,20,-7)] if not nc else []
    if nc:
        f += [ln(-20,0,20,0)]
    else:
        f += [ln(-18,-10,18,-10)]
    # Stem and mushroom/T actuator: NOT an electrical connection.
    f += [ln(0,-28,0,-12),ln(-9,-28,9,-28)]
    return f


def changeover_two_positions():
    """Reference 2: one common contact and two selectable positions (SPDT)."""
    f=[ln(-60,0,-24,0),ln(24,-20,60,-20),ln(24,20,60,20)]
    f+=contact_ring(-20,0)+contact_ring(20,-20)+contact_ring(20,20)
    f += [ln(-20,0,20,-20)]
    return f


def changeover_multiposition():
    """Reference 2: four fixed contacts above one moving common blade."""
    f=[]
    for x in (-60,-20,20,60):
        f += [ln(x,-60,x,-24)]
        f += contact_ring(x,-20)
    f += [ln(0,24,0,60)]
    f += contact_ring(0,20)
    # Blade connects the lower common to the far-right fixed contact.
    f += [ln(0,20,60,-20)]
    return f


def selector_rotary(positions=3):
    """Selector multiposición: borne común inferior y N contactos superiores.

    Geometría ortogonal en rejilla de 20, con uno de los contactos
    representado como seleccionado. Es un símbolo de dibujo; no simula.
    """
    if type(positions) is not int or not 2 <= positions <= 12:
        raise ValueError('Cantidad de posiciones de selector inválida.')
    fixed=[-(positions-1)*20+i*40 for i in range(positions)]
    f=[]
    for xx in fixed:
        f.extend([ln(xx,-60,xx,-24), *contact_ring(xx,-20)])
    f.extend([ln(0,24,0,60), *contact_ring(0,20)])
    # El brazo móvil es oblicuo y llega al contacto más a la derecha.
    f.append(ln(0,20,fixed[-1],-20))
    return f


def horizontal_double_switch():
    """Reference 2: two open circuits linked by a mechanical dashed rod."""
    f=[]
    for y in (-20,20):
        f.extend([ln(-60,y,-24,y),ln(24,y,60,y)])
        f += contact_ring(-20,y)+contact_ring(20,y)
        f += [ln(-20,y,13,y-14)]
    # Mechanical coupling: dashed, and intentionally NOT a conductor.
    f += [dl(0,-32,0,8)]
    return f


def process_switch(letter):
    return [ln(0,-40,0,-18), rc(-24,-18,24,18), ln(0,18,0,40), tx(-9,0,letter,13), ln(8,-4,18,-4), ln(18,-4,18,7)]


def _sensor_contact(nc=False):
    """Contacto interior de sensor, según la muestra NA/NC proporcionada.

    NA: lámina móvil separada del contacto fijo superior.
    NC: lámina móvil unida al contacto fijo superior en reposo.
    Mantener ambos trazos distintos también a escala de icono.
    """
    if nc:
        # Contacto fijo en forma de U abierta hacia abajo y lámina móvil
        # que toca su extremo derecho, como en la referencia NC.
        return [ln(24,-15,24,-8),
                ln(24,-8,33,-8),
                ln(27,12,33,-8)]
    # Contacto fijo pequeño, aislado del extremo de la lámina móvil.
    return [ln(31,-15,31,-11),
            ln(27,12,19,-7)]


def sensor_block(kind):
    """Sensor de 2 bornes, fiel al dibujo facilitado por el usuario.

    Marco ancho 88x42 (proporción de la foto), icono físico a la izquierda,
    rombo central con raya vertical y contacto realmente NA/NC a la derecha.
    Los terminales siguen en (0,-40) y (0,40) para garantizar conexión.
    """
    nc=kind.endswith('_nc')
    f=[ln(0,-40,0,-21),rc(-44,-21,44,21),ln(0,21,0,40)]
    if 'inductive' in kind:
        # Detector inductivo: barra sólida estrecha atravesada por el eje.
        f += [fr(-38,-9,-32,9),ln(-35,-14,-35,14)]
    elif 'capacitive' in kind:
        # Detector capacitivo: placas paralelas, como la foto original.
        f += [ln(-41,-4,-26,-4),ln(-41,4,-26,4),
              ln(-33,-14,-33,-5),ln(-33,5,-33,14)]
    elif 'magnetic' in kind:
        # Detector magnético: núcleo en U grueso, abierto a la derecha.
        f += [fr(-39,-11,-34,11),fr(-39,-11,-29,-7),fr(-39,7,-29,11)]
    # Rombo central, dos lados simétricos y eje vertical interno visible.
    f += [ln(-8,0,3,-12),ln(3,-12,14,0),
          ln(14,0,3,12),ln(3,12,-8,0),
          ln(3,-8,3,8)]
    # Contacto de salida, no una simple marca de estado.
    f += _sensor_contact(nc=nc)
    return f


def photoelectric_shape():
    """Barrera fotoeléctrica de 5 bornes conforme a la muestra visual.

    Conserva todos los puntos de conexión existentes; solo se ordenan los
    detalles interiores del emisor/receptor y las flechas ópticas.
    """
    f=[rc(-27,-24,27,24),
       ln(-12,-40,-12,-24),ln(12,-40,12,-24),
       ln(-18,24,-18,40),ln(0,24,0,40),ln(18,24,18,40)]
    # Pantalla del receptor con retorno perpendicular, sin trazos cortados.
    f += [ln(-18,14,-18,-12),ln(-18,-12,-4,-12),
          ln(-4,-12,-11,4),ln(-11,4,-11,14)]
    # Emisor en la parte superior derecha y flecha de salida.
    f += [fr(9,-16,15,-11),ln(12,-11,12,-3),
          ln(9,-4,12,1),ln(15,-4,12,1),
          ln(27,-9,36,-9),ln(32,-13,36,-9),ln(32,-5,36,-9)]
    # Elemento óptico inferior con flecha de retorno.
    f += [ln(8,17,16,8),ln(16,8,16,18),
          ln(27,9,36,9),ln(31,5,27,9),ln(31,13,27,9)]
    return f


def motor(kind):
    f=[ci(0,3,28),tx(0,-2,'M',21),
       tx(0,16,'1~' if kind=='motor_1ph' else '3~',12)]
    xs=(-20,20) if kind=='motor_1ph' else (-20,0,20)
    for x in xs:
        y=3-math.sqrt(28**2-x**2)
        f.append(ln(x,-40,x,round(y,2)))
    return f


def sounder():
    # Zumbador / avisador acústico: transductor con apertura sonora, más
    # distinguible de una bobina o un resistor rectangular.
    f=leads(-18,18)
    f += [ln(0,-18,0,-12),rc(-11,-12,3,12),ln(3,-8,13,-13),
          ln(13,-13,13,13),ln(13,13,3,8),ln(0,12,0,18)]
    f += arcs(13,0,5,8,-55,55,7)
    f += arcs(13,0,11,14,-55,55,9)
    return f




def compact_thermal_3p():
    """Relé térmico tripolar ópticamente proporcionado a sus contactos.

    Un cuerpo tripolar único y compartimentado reemplaza las tres cajas
    sobredimensionadas. Conserva EXACTAMENTE los seis extremos (-20/0/20,
    +/-40) del proyecto y la independencia eléctrica de las tres fases.
    Los detalles son vectoriales y mantienen la legibilidad en A4.
    """
    f=[]
    for x in (-20,0,20):
        f += [ln(x,-40,x,-12),ln(x,12,x,40)]
    f += [rc(-27,-12,27,12),ln(-9,-12,-9,12),ln(9,-12,9,12)]
    # Signo térmico dentro de cada compartimento, sin crear un puente
    # eléctrico entre fases.
    for x in (-20,0,20):
        f += [ln(x-4,-6,x+3,-6),ln(x+3,-6,x+3,3),ln(x+3,3,x-4,3)]
    return f


def compact_sensor_primitives(kind):
    """Cuerpo de sensor compacto, diseñado ópticamente en vez de deformado.

    Los bornes no cambian (0,+/-40) y se mantienen NA/NC distinguibles.
    Tamaño óptico sin escalar: 66 x 34, frente a 88 x 42 anterior.
    """
    nc=kind.endswith('_nc')
    f=[ln(0,-40,0,-17),rc(-33,-17,33,17),ln(0,17,0,40)]
    if 'inductive' in kind:
        # Barra y núcleo inductivo al lado izquierdo.
        f += [fr(-29,-8,-25,8),ln(-27,-11,-27,11)]
    elif 'capacitive' in kind:
        # Placas enfrentadas del sensor capacitivo.
        f += [ln(-29,-9,-29,9),ln(-25,-9,-25,9),
              ln(-32,-6,-29,-6),ln(-25,6,-22,6)]
    elif 'magnetic' in kind:
        # Núcleo magnético en U, abierto hacia el centro.
        f += [fr(-30,-9,-27,9),fr(-30,-9,-23,-6),fr(-30,6,-23,9)]
    # Rombo detector central, manteniendo separación respecto al icono
    # tecnológico y al contacto de salida.
    f += [ln(-6,0,2,-9),ln(2,-9,10,0),ln(10,0,2,9),ln(2,9,-6,0),
          ln(2,-6,2,6)]
    # Pequeño contacto fijo con travesaño: NC cerrado, NA con luz
    # perceptible incluso en el símbolo compacto impreso a escala.
    f += [ln(27,-12,27,-7),ln(24,-7,30,-7)]
    if nc:
        f += [ln(17,9,27,-7)]
    else:
        f += [ln(17,9,22,-1)]
    return f


def compact_multipole_protection(kind):
    """Dibujo uniforme de protecciones multipolares, sin modificar bornes.

    La vinculación de los contactos es mecánica, nunca un puente eléctrico.
    Los puntos de conexión permanecen idénticos a los del motor de dibujo.
    """
    differential=kind.startswith('differential_')
    motor=kind=='motor_protector_3p'
    if kind in ('breaker_2p','differential_2p'):
        xs=(-10,10)
    elif kind=='breaker_4p':
        xs=(-60,-20,20,60)
    elif kind=='differential_4p':
        xs=(-30,-10,10,30)
    else:
        xs=(-20,0,20)
    f=[]
    for x in xs:
        # Contacto móvil abierto, claramente separado del contacto fijo.
        f.extend((ln(x,-40,x,-18),ln(x,-18,x+7,6),
                  ln(x,16,x+7,16),ln(x,16,x,40)))
        if differential:
            f.extend((ln(x-3,20,x+3,20),))
        elif not motor:
            f.extend((ln(x-4,-22,x+2,-22),))
    if motor:
        # Un único cuerpo de protección tripolar compartimentado.
        f.append(rc(xs[0]-9,12,xs[-1]+9,30))
        for left_pole,right_pole in zip(xs,xs[1:]):
            mx=(left_pole+right_pole)/2
            f.append(ln(mx,12,mx,30))
        for x in xs:
            f.extend((ln(x-4,18,x+3,21),ln(x+3,21,x-4,24)))
    # Un único mando de disparo común lateral.
    left=xs[0]-22
    f.extend((rc(left,-11,left+12,7),ln(left+6,-11,left+6,7),
              dl(left+12,-2,xs[0]-5,-2)))
    if len(xs)>1 and not motor:
        f.append(dl(xs[0]+10,25,xs[-1]+10,25))
    if differential:
        # Marca funcional orientativa; no certifica IEC 60617.
        f.extend(arcs(left+6,16,5,4,0,180,24))
    return f


def compact_optoelectric_barrier():
    """Emisor, receptor y flechas legibles con cinco bornes invariantes."""
    f=[rc(-24,-19,24,19)]
    f.extend((ln(-12,-40,-12,-19),ln(12,-40,12,-19),
              ln(-18,19,-18,40),ln(0,19,0,40),ln(18,19,18,40)))
    f.extend((ln(-17,-10,-17,11),ln(-17,-10,-6,-10),
              ln(-6,-10,-12,3),ln(-12,3,-12,11),
              fr(9,-11,14,-7),ln(11,-7,11,-1),
              ln(8,-2,11,2),ln(14,-2,11,2),
              ln(7,14,15,6),ln(15,6,15,15),
              ln(24,-7,32,-7),ln(28,-10,32,-7),ln(28,-4,32,-7),
              ln(24,7,32,7),ln(28,4,24,7),ln(28,10,24,7)))
    return f


def compact_symbol_primitives(kind):
    """Acabado óptico del catálogo compacto sin cambiar bornes eléctricos.

    Los ajustes son específicos por familia y preservan los puntos de
    conexión históricos. No cambian símbolos a escala original del editor.
    """
    if kind in ('plc_input','plc_output'):
        f=[rc(-27,-33,27,34),ln(-27,-12,27,-12)]
        if kind=='plc_input': f.append(ln(0,-60,0,-33))
        else: f.append(ln(0,34,0,60))
        return f
    if kind=='power_supply':
        return [rc(-40,-40,40,40),
                ln(-60,-20,-40,-20),ln(-60,20,-40,20),
                ln(40,-20,60,-20),ln(40,20,60,20),
                ln(-40,40,40,-40),
                tx(-16,-15,'~',15),tx(17,14,'=',14),
                tx(-33,-27,'L',10),tx(-33,27,'N',10),
                tx(33,-27,'+',10),tx(33,27,'−',10)]
    if kind in ('breaker_2p','breaker_3p','breaker_4p',
                'differential_2p','differential_4p','motor_protector_3p'):
        return compact_multipole_protection(kind)
    if kind=='photoelectric_barrier':
        return compact_optoelectric_barrier()
    if kind=='thermal_3p':
        return compact_thermal_3p()
    if kind in ('sensor_inductive_no','sensor_inductive_nc',
                'sensor_capacitive_no','sensor_capacitive_nc',
                'sensor_magnetic_no','sensor_magnetic_nc'):
        return compact_sensor_primitives(kind)
    if kind=='contactor_3p':
        f=[]
        for x in (-20,0,20):
            f += [ln(x,-40,x,-16),ln(x,-16,x+9,7),
                  ln(x,16,x+8,16),ln(x,16,x,40),
                  dl(x+11,8,x+11,23)]
        f.append(dl(-9,25,31,25))
        return f
    return symbol_primitives(kind)


def symbol_primitives(kind):
    if kind=='plc_input':
        return [rc(-40,-50,40,50),ln(-40,-25,40,-25),ln(0,-60,0,-50)]
    if kind=='plc_output':
        return [rc(-40,-50,40,50),ln(-40,-25,40,-25),ln(0,50,0,60)]
    if kind=='power_supply':
        # Un marco AC/DC de 100 x 100 unidades, según el recuadro de
        # referencia, con cuatro bornes claramente fuera del marco.
        return [rc(-50,-50,50,50),
                ln(-60,-20,-50,-20), ln(-60,20,-50,20),
                ln(50,-20,60,-20), ln(50,20,60,20),
                ln(-50,50,50,-50),
                tx(-23,-17,'~',16), tx(21,18,'=',16),
                tx(-43,-29,'L',10), tx(-43,31,'N',10),
                tx(42,-29,'+',11), tx(42,31,'−',11)]
    if kind=='breaker_2p': return multipole_breaker(2,False,False)
    if kind=='breaker_3p': return multipole_breaker(3,False,False)
    if kind=='breaker_4p': return multipole_breaker(4,False,False,aligned_four_pole=True)
    if kind=='differential_2p': return multipole_breaker(2,True,False)
    if kind=='differential_4p': return multipole_breaker(4,True,False)
    if kind=='motor_protector_3p': return multipole_breaker(3,False,True)
    if kind=='switch_horizontal_no': return horizontal_switch(False)
    if kind=='switch_horizontal_nc': return horizontal_switch(True)
    if kind=='pushbutton_horizontal_no': return horizontal_pushbutton(False)
    if kind=='pushbutton_horizontal_nc': return horizontal_pushbutton(True)
    if kind=='changeover_2pos': return changeover_two_positions()
    if kind=='changeover_multi': return changeover_multiposition()
    if kind=='selector_multi': return selector_rotary(3)
    if kind=='switch_double_horizontal': return horizontal_double_switch()
    if kind=='directional_terminal': return directional_terminal_shape()
    if kind=='directional_terminal_in': return directional_terminal_shape(inbound=True)
    if kind=='pressostat': return process_switch('P')
    if kind=='vacuostat': return process_switch('V')
    if kind=='thermostat': return process_switch('T')
    if kind in ('sensor_inductive_no','sensor_inductive_nc','sensor_capacitive_no','sensor_capacitive_nc','sensor_magnetic_no','sensor_magnetic_nc'):
        return sensor_block(kind)
    if kind=='photoelectric_barrier': return photoelectric_shape()
    contacts={
        'contact_no','contact_nc','contact_timer_no','contact_timer_nc',
        'thermal_nc','thermal_no','limit_no','limit_nc',
        'selector_no','selector_nc',
    }
    if kind in contacts:
        nc=kind in ('contact_nc','contact_timer_nc','thermal_nc','limit_nc','selector_nc')
        f=contact(nc)
        if kind.startswith('contact_timer_'):f += time_mark()
        if kind.startswith('thermal_'):f += overload_mark()
        if kind.startswith('limit_'):f += roller_mark()
        if kind.startswith('selector_'):f += selector_mark()
        return f
    if kind in ('pushbutton','pushbutton_nc','emergency_nc'):
        return push_contact(kind!='pushbutton')+push_mark(kind=='emergency_nc')
    if kind=='pushbutton_double':return push_double()
    if kind in ('coil','coil_contactor','coil_timer_on','coil_timer_off','coil_solenoid'):
        return coil(kind)
    if kind in ('fuse','disconnect_1p','breaker_1p'):return protection(kind)
    if kind in ('thermal_3p','contactor_3p'):return power(kind)
    if kind in ('motor_1ph','motor_3ph'):return motor(kind)
    if kind=='lamp':
        return leads(-16,16)+[ci(0,0,16),ln(-11,-11,11,11),ln(11,-11,-11,11)]
    if kind in ('voltmeter','ammeter'):
        return leads(-22,22)+[ci(0,0,22),tx(0,0,'V' if kind=='voltmeter' else 'A',22)]
    if kind=='buzzer':return sounder()
    if kind=='ground':
        return [ln(0,-40,0,-3),ln(-21,-3,21,-3),ln(-14,3,14,3),ln(-7,9,7,9)]
    if kind=='terminal':
        return [ci(0,0,6)]
    if kind=='junction':
        return [dt(0,0,3.8)]
    raise ValueError(f'Símbolo sin geometría: {kind}')
