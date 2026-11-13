# Electrical Work Compacto V0.4 — desarrollo

**Rama:** `desarrollo-compacto`  
**Estado:** última versión de la línea Compacto, todavía en desarrollo y pruebas.

Esta rama sirve para perfeccionar la presentación y las proporciones de Electrical Work **sin alterar la versión V0.38.3**, que se conserva en la rama `main` como referencia funcional para el trabajo diario.

> No sustituir ni fusionar automáticamente esta rama con `main`. Cualquier cambio de versión de trabajo requiere aprobación expresa.

## Qué incorpora Compacto V0.4

- Escala compacta real del **70 %** y rejilla fina.
- Ajustes de proporciones del relé térmico tripolar.
- Revisión gráfica de seis sensores inductivos, capacitivos y magnéticos (NA y NC).
- Conservación de los puntos de conexión y del cableado de los símbolos.
- Edición de referencias, esquemas de varias hojas y salida PDF/SVG vectorial.
- Módulo `quality_render.py` para el tratamiento gráfico.

Los cambios concretos y las comprobaciones documentadas están en `CAMBIOS_V0_4.txt`, `COMPROBACIONES_V0_4.txt` y `LEEME.txt`.

## Ejecutar en Windows

1. Descarga esta rama y descomprímela en una carpeta independiente de V0.38.3.
2. Ten instalado Python 3 con Tkinter.
3. Ejecuta `INICIAR_WINDOWS.bat`.
4. Para consultar errores de arranque, utiliza `INICIAR_CON_CONSOLA.bat`.

Pillow puede utilizarse para el suavizado gráfico; el lanzador permite continuar con el renderizado clásico si no se instala. Esta entrega es **código ejecutable mediante Python**, no un instalador EXE independiente.

## Archivos principales

- `electrical_work.py`: interfaz del editor.
- `core.py`, `symbology.py`: lógica y simbología.
- `documentation.py`, `page_layout.py`, `pdf_export.py`: documentación, hojas y PDF.
- `quality_render.py`: mejora de presentación gráfica.
- `INICIAR_WINDOWS.bat`, `INICIAR_CON_CONSOLA.bat`: lanzadores Windows.
- `COMPARATIVA_V0_4.png`, `PREVIA_EDITOR_V0_4.png`: imágenes ilustrativas del desarrollo.

## Proyectos y privacidad

Este repositorio no incluye proyectos personales `.ework` ni sus exportaciones. Las referencias a archivos de ejemplo en `LEEME.txt` corresponden al paquete de pruebas original: **esos ejemplos no se distribuyen en este repositorio**.

Conserva tus proyectos y copias de seguridad por separado. Revisa las futuras subidas a GitHub, ya que `.gitignore` no bloquea archivos añadidos manualmente desde la web.

## Compatibilidad y precauciones

La documentación de V0.4 indica compatibilidad de apertura con proyectos de V0.38.3 y versiones Compacto anteriores. Guarda una copia de cualquier proyecto antes de editarlo con esta rama. Quedan pendientes las pruebas finales en Windows y la comprobación física de impresión.

**Electrical Work es un editor de esquemas:** no simula ni certifica la seguridad de una instalación eléctrica.


## Revisión gráfica posterior a Compacto V0.4 (desarrollo, sin nueva versión)

Cambios en curso sobre \`desarrollo-compacto\`, **no publicados como nueva versión**:

- Proporciones y separación de mecanismos en protecciones de 2, 3 y 4 polos, diferenciales y guardamotor.
- Barrera fotoeléctrica más legible; contactos NA y NC internos de sensores diferenciados.
- Antialiasing a 4× con terminaciones de trazos redondeadas y rellenos opacos coherentes con PDF/SVG; Pillow continúa siendo opcional.
- No se cambian los puntos eléctricos de conexión, el formato de proyecto ni la interfaz aprobada.
- Regresión repetible: \`python -m unittest discover -s tests -v\` (63 tipos, 4 orientaciones, exportación y guardado). El resultado en Windows e impresión física quedan pendientes.

**Evaluación del ecosistema ArtCraft:** se ha revisado [VectorCraft](https://github.com/storytold/vectorcraft) y su [arquitectura de renderizado](https://github.com/storytold/vectorcraft/blob/main/docs/architecture.md).
VectorCraft es MIT/Apache-2.0, pero las marcas y los recursos de terceros tienen condiciones propias. Se han adoptado **criterios técnicos de calidad vectorial**, sin copiar código ni integrar motores/librerías nuevos. Su motor Rust no forma parte de esta rama. Tampoco se ha integrado Godot ni REA: no se confirmó acceso operativo a REA y sustituir el motor requiere una decisión técnica expresa.

**Seguridad:** V0.4 sigue siendo la versión entregada como referencia en esta línea; \`main\` conserva V0.38.3. No se han generado releases o etiquetas nuevas. La validación automática no equivale a aprobación del usuario.
