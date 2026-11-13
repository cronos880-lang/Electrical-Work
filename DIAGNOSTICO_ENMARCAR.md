# Diagnóstico de Enmarcar — Electrical Work Compacto V0.5.2

**Rama:** `desarrollo-compacto`. **Estado:** corrección de código en revisión, sin nueva versión, etiqueta, release ni ZIP. **Base:** commit `760f9dc` (V0.5.2 de prueba). No modificar `main` (V0.38.3).

## Síntoma comunicado
Al intentar usar «Enmarcar» / selección múltiple, el arrastre desplaza la hoja en vez de dibujar y aplicar un recuadro.

## Causas identificadas en el código
1. `on_canvas_up()` ejecutaba `_set_tool('select')` tras **cada** selección, aunque el usuario no pidiera cambiar de modo. El siguiente arrastre en espacio vacío activaba `scan_dragto` en el modo Puntero.
2. El desplegable elegía herramienta en `<Button-1>`, destruyendo el propio widget antes del evento de soltar el botón. Es un riesgo adicional de eventos; no se ha demostrado que sea la causa del fallo en Windows.
3. Abrir el grupo Líneas cambiaba silenciosamente a «Recta» incluso si estaba activo «Enmarcar».

## Cambios realizados
- «Enmarcar» se mantiene como segunda herramienta del desplegable (tras «Recta»).
- La selección de herramienta ocurre al soltar sobre su icono, sin destruir el menú durante la pulsación.
- Abrir el desplegable ya no cambia la herramienta activa.
- Una vez activado, «Enmarcar» permanece activo tras soltar, con cursor de precisión y mensaje con el número de objetos elegidos. Para mover la selección se pulsa **Esc** (Puntero).
- Se da prioridad a un marco iniciado frente a la lógica de desplazamiento de la hoja.
- La geometría de selección por intersección, los símbolos, cables, motor, PDF, SVG y formato `.ework` permanecen sin modificar.
- Pruebas integradas añadidas en `tests/test_enmarcar_gui.py` para segundo icono, selección consecutiva, cables que atraviesan el recuadro y zoom.

## Pruebas efectuadas en esta revisión
- **Tkinter real en Xvfb (simulación aislada, no la aplicación completa):** 2 pruebas sobre la secuencia de eventos y reproducción del fallo anterior; 4 pruebas de selección en un Canvas real para dos símbolos, intersección parcial, arrastre invertido, cable que cruza y zoom: **6/6 superadas**.
- **Geometría aislada:** 12 casos de segmentos (incluidos extremos y segmentos degenerados): **1/1 test con 12 subcasos superado**.
- **Revisión estructural:** verificado que solo `electrical_work.py` y el nuevo test GUI cambian respecto a V0.5.2, antes de añadir estas notas.

## Pendiente antes de entregar una actualización
- Ejecutar el **programa completo** con `python -m unittest discover -s tests -v` y pruebas manuales de GUI real.
- Confirmar en Windows que la instalación del usuario carga exactamente el `electrical_work.py` actualizado; el acceso directo podría apuntar a otra carpeta.
- Probar con un proyecto real sin modificar el archivo original; comprobar selección, movimiento del grupo, deshacer, guardado y reapertura, con copia de seguridad.
- Ningún test aislado ni commit equivale a aprobación del usuario.

## Recuperación
No se ha modificado ni borrado ningún proyecto `.ework`. Para recuperar el código anterior a esta revisión, restaurar **únicamente** `electrical_work.py` desde el commit base `760f9dc`; conservar `core.py`, los datos, la carpeta de proyectos y el resto de archivos. No fusionar con `main` ni aplicar estos cambios en V0.38.3.

## Herramientas y dependencias
Código en Python >=3.9; Tkinter, sin dependencia añadida (Pillow continúa siendo opcional). Utilizados GitHub y pruebas Tkinter/Xvfb. Se evaluaron ArtCraft, Rust y Godot como innecesarios para un fallo de eventos Tk. REA no aparece como MCP conectado en esta sesión, y no se ha utilizado.
