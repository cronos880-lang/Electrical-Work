# Electrical Work Compacto V0.5.3 — entrega COMPLETA de prueba

**Estado:** versión desarrollada y preparada para probar en Windows. **No es una versión oficial aprobada**; la aprobación final corresponde al usuario. La referencia funcional de `main` (V0.38.3) no se modifica.

## Qué incluye esta versión

- **Diseño clásico recuperado**, exactamente la cabecera «EW», el encabezado y los botones originales de Compacto, sin el cambio gráfico descartado.
- Proporciones compactas, barras de herramientas, símbolos y documentación de la línea Compacto V0.5.
- **Enmarcar como segunda opción** del desplegable Líneas, justo después de la recta.
- Enmarcar conserva el modo tras una selección; el recuadro selecciona símbolos tocados y cables que atraviesan su área, sin desplazar la hoja. `Esc` retorna al puntero para mover el grupo.
- El zoom con rueda, desplazamiento de hoja con puntero, selección, movimiento de grupo y deshacer siguen disponibles.
- Versionado visible: **V0.5.3**, sin cambio de formato de proyecto.

## Instalación COMPLETA y segura

1. Cierra cualquier Electrical Work abierto y conserva la carpeta anterior.
2. **Extrae el ZIP completo en una carpeta nueva** como `Electrical_Work_Compacto_V0_5_3`, no encima de otra instalación.
3. Mantén los proyectos `.ework`, imágenes privadas y copias de seguridad **fuera de esta carpeta**. El paquete no incluye ni modifica proyectos personales.
4. Ejecuta `INICIAR_WINDOWS.bat`; requiere **Python >=3.9 con Tkinter**. El lanzador conserva la posibilidad de instalar **Pillow >=9** para suavizado, pero Pillow sigue siendo opcional y el programa puede arrancar sin él.
5. Verifica que el título de la ventana indique **COMPACTO V0.5.3** y que se conserve la cabecera original «EW».
6. Abre **una copia** de un proyecto de prueba y comprueba selección por marco, zoom, movimiento, deshacer, guardar y reapertura, PDF y documentación antes de trabajar con originales.

**No es instalador EXE**: es una carpeta completa en Python con dos lanzadores BAT.

## Recuperación sin pérdida de datos

Cierra V0.5.3 y vuelve a ejecutar la **carpeta anterior conservada**. No borres ni sustituyas los `.ework`. Si necesitas compartir proyectos entre versiones, trabaja primero sobre copias; no conviertas ni sobrescribas el original sin una copia verificada. No se han realizado migraciones de datos.

## Componentes incluidos

- `electrical_work.py`: interfaz principal.
- `core.py`, `symbology.py`, `quality_render.py`: geometría, símbolos y renderizado.
- `documentation.py`, `page_layout.py`, `pdf_export.py`: documentos, presentación y PDF.
- `INICIAR_WINDOWS.bat` y `INICIAR_CON_CONSOLA.bat`: arranque y diagnóstico.
- `tests/test_render_regression.py` y `tests/test_enmarcar_gui.py`: comprobaciones automatizadas (uso opcional).
- `LEEME_PRIMERO_V0_5_3.txt`: instrucciones de entrega.

## Pruebas, límites y verificación

- Revisada la identidad exacta de la interfaz restaurada respecto al código anterior al cambio gráfico y la posición de «Enmarcar» en la barra.
- Cinco pruebas aisladas con Tkinter/Xvfb y geometría de selección pasaron en el entorno disponible, pero **no importan ni ejercitan la aplicación completa**.
- Los tests incluidos contra `ElectricalWorkApp` todavía requieren ejecución en la aplicación real; pueden ejecutarse con `python -m unittest discover -s tests -v`.
- **Pendiente**: prueba funcional completa en Windows del usuario y prueba de impresión/exportación física. No confundir comprobación de código con instalación aprobada.

**Dependencias:** Python >=3.9; Tkinter (incluido normalmente con Python en Windows); Pillow >=9 solo opcional. No se añaden nuevas librerías. No se incluye muestra de proyectos, datos ni recursos privados.

**Herramientas:** GitHub para fuentes y entrega; evaluación de ArtCraft, REA, Godot y Rust: no son necesarios para empaquetar y preservar el editor Tkinter, y no se han integrado. REA no figura como MCP accesible en este chat.
