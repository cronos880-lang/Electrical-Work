"""Documentación editable de referencias vinculada al proyecto Electrical Work.

Las filas automáticas salen únicamente de aparatos documentables. Las filas
manuales y la ocultación de filas automáticas se guardan dentro del .ework.
Borrar una fila documental NUNCA borra el símbolo del plano.
"""
from __future__ import annotations
import csv
import uuid
from pathlib import Path
from core import SYMBOL_NAMES, plc_channel_name, validate_project

# Los bornes, conexiones, textos, imágenes y tierras no son aparatos que
# requieran ficha de descripción. Las líneas se almacenan aparte como cables.
EXCLUDED_KINDS = frozenset({
    'terminal', 'directional_terminal', 'directional_terminal_in', 'junction', 'ground', 'text', 'image',
})

GROUPS = (
    'Entradas PLC', 'Salidas PLC', 'Relés y bobinas', 'Contactos', 'Mando',
    'Sensores', 'Térmicos', 'Protecciones', 'Contactores', 'Motores',
    'Actuadores', 'Señalización', 'Medida',
)
ORDER = {group: index for index, group in enumerate(GROUPS)}

RELAY_KINDS = frozenset({'coil','coil_contactor','coil_timer_on','coil_timer_off'})
THERMAL_KINDS = frozenset({'thermal_no','thermal_nc','thermal_3p','motor_protector_3p'})
SENSOR_KINDS = frozenset({'photoelectric_barrier','pressostat','vacuostat','thermostat',
    'limit_no','limit_nc'})
PROTECTION_KINDS = frozenset({'fuse','breaker_1p','breaker_2p','breaker_3p','breaker_4p',
    'differential_2p','differential_4p','disconnect_1p'})
MOTOR_KINDS = frozenset({'motor_1ph','motor_3ph'})
ACTUATOR_KINDS = frozenset({'coil_solenoid'})
SIGNAL_KINDS = frozenset({'lamp','buzzer'})
MEASURE_KINDS = frozenset({'voltmeter','ammeter'})
COMMAND_KINDS = frozenset({'pushbutton','pushbutton_nc','pushbutton_double',
    'pushbutton_horizontal_no','pushbutton_horizontal_nc',
    'emergency_nc','selector_no','selector_nc','selector_multi'})
CONTACT_KINDS = frozenset({'contact_no','contact_nc','contact_timer_no','contact_timer_nc',
    'switch_horizontal_no','switch_horizontal_nc','changeover_2pos','changeover_multi','switch_double_horizontal'})


def _classify(kind):
    if kind in EXCLUDED_KINDS:
        return None
    if kind == 'plc_input': return 'Entradas PLC'
    if kind == 'plc_output': return 'Salidas PLC'
    if kind in RELAY_KINDS: return 'Relés y bobinas'
    if kind in THERMAL_KINDS: return 'Térmicos'
    if kind.startswith('sensor_') or kind in SENSOR_KINDS: return 'Sensores'
    if kind in PROTECTION_KINDS: return 'Protecciones'
    if kind == 'contactor_3p': return 'Contactores'
    if kind in MOTOR_KINDS: return 'Motores'
    if kind in ACTUATOR_KINDS: return 'Actuadores'
    if kind in SIGNAL_KINDS: return 'Señalización'
    if kind in MEASURE_KINDS: return 'Medida'
    if kind in COMMAND_KINDS: return 'Mando'
    if kind in CONTACT_KINDS: return 'Contactos'
    # Los aparatos nuevos no clasificados requieren decisión explícita:
    # no volver a crear filas genéricas «Elementos» ni incluir auxiliares.
    return None


def documentation_rows(project):
    """Devuelve las filas visibles, automáticas y añadidas por el usuario."""
    saved = project.get('documentation', {})
    hidden = set(project.get('documentation_hidden', []))
    rows = []
    for sheet_number, doc in enumerate(project['sheets'], 1):
        sheet = f'{sheet_number:03d}'
        for item in doc['elements']:
            kind = item['kind']
            identifier = item['id']
            if kind == 'plc_module':
                for direction, count, group in (
                    ('I', item['plc_inputs'], 'Entradas PLC'),
                    ('Q', item['plc_outputs'], 'Salidas PLC'),
                ):
                    for index in range(count):
                        key = f'plc:{identifier}:{direction}:{index}'
                        if key not in hidden:
                            rows.append(dict(key=key, group=group,
                                reference=plc_channel_name(direction, index),
                                sheets=sheet, description=saved.get(key, ''), manual=False))
                continue
            group = _classify(kind)
            if not group:
                continue
            key = f'element:{identifier}'
            if key in hidden:
                continue
            reference = item.get('label', '').strip() or SYMBOL_NAMES.get(kind, kind)
            rows.append(dict(key=key, group=group, reference=reference,
                sheets=sheet, description=saved.get(key, ''), manual=False))
    for record in project.get('documentation_manual', []):
        rows.append(dict(key='manual:'+record['id'], group=record['group'],
            reference=record['reference'], description=record.get('description', ''),
            sheets=record.get('sheets', ''), manual=True))
    rows.sort(key=lambda r:(ORDER.get(r['group'],99), r['reference'].casefold(), r['sheets'], r['key']))
    return rows


def _validate_text(value, max_len, field, *, required=False):
    if not isinstance(value, str) or len(value)>max_len or any(c in value for c in '\r\n'):
        raise ValueError(f'{field}: texto inválido (máximo {max_len} caracteres, una línea).')
    value=value.strip()
    if required and not value:
        raise ValueError(f'Introduce {field.lower()}.')
    return value


def set_description(project, key, description):
    _validate_text(key, 140, 'Identificador', required=True)
    description = _validate_text(description, 600, 'Descripción')
    valid = {row['key'] for row in documentation_rows(project)}
    if key not in valid:
        raise ValueError('La fila ya no está en la documentación del proyecto.')
    if key.startswith('manual:'):
        identifier = key.removeprefix('manual:')
        for record in project.get('documentation_manual', []):
            if record['id']==identifier:
                record['description']=description
                return
        raise ValueError('No existe la fila manual.')
    docs = project.setdefault('documentation', {})
    if description:
        docs[key]=description
    else:
        docs.pop(key, None)


def add_manual_row(project, group, reference, description='', sheets=''):
    group = _validate_text(group, 80, 'Familia', required=True)
    reference = _validate_text(reference, 100, 'Referencia', required=True)
    description = _validate_text(description, 600, 'Descripción')
    sheets = _validate_text(sheets, 30, 'Hoja')
    record = dict(id=uuid.uuid4().hex, group=group, reference=reference,
                  description=description, sheets=sheets)
    project.setdefault('documentation_manual', []).append(record)
    return 'manual:'+record['id']


def update_manual_row(project, key, group, reference, description, sheets):
    group = _validate_text(group, 80, 'Familia', required=True)
    reference=_validate_text(reference,100,'Referencia',required=True)
    description=_validate_text(description,600,'Descripción')
    sheets=_validate_text(sheets,30,'Hoja')
    for rec in project.get('documentation_manual', []):
        if key=='manual:'+rec['id']:
            rec.update(group=group,reference=reference,description=description,sheets=sheets)
            return
    raise ValueError('No existe la fila manual.')


def delete_documentation_row(project, key):
    """Quita una fila documental sin eliminar ningún componente del esquema."""
    visible = {row['key'] for row in documentation_rows(project)}
    if key not in visible:
        raise ValueError('Selecciona una fila existente de la documentación.')
    if key.startswith('manual:'):
        identifier=key.removeprefix('manual:')
        project['documentation_manual']=[r for r in project.get('documentation_manual',[])
                                         if r['id'] != identifier]
    else:
        hidden=project.setdefault('documentation_hidden',[])
        if key not in hidden:
            hidden.append(key)


def restore_hidden_rows(project):
    """Recupera las filas automáticas ocultadas por el usuario."""
    count=len(project.get('documentation_hidden',[]))
    project['documentation_hidden']=[]
    return count


def export_documentation_csv(project, path):
    """Tabla separada por punto y coma compatible con Excel en España."""
    validate_project(project)
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        out=csv.writer(f,delimiter=';',quoting=csv.QUOTE_MINIMAL)
        out.writerow(['Familia','Referencia','Descripción','Hoja'])
        for row in documentation_rows(project):
            out.writerow([row['group'],row['reference'],row['description'],row['sheets']])
