# Electrical Work V0.38.3 — versión de trabajo

**Versión de referencia funcional.** Esta rama del repositorio debe permanecer separada de las pruebas de Compacto V0.4. No se ha cambiado ninguna línea del motor Python de la entrega original V0.38.3.

## Ejecutar en Windows

1. Descarga el código de esta rama y descomprímelo en una carpeta nueva.
2. Instala Python 3.9 o superior con Tkinter (normalmente incluido en la instalación oficial de Python para Windows).
3. Haz doble clic en `INICIAR_WINDOWS.bat`.
4. Para depurar un fallo, ejecuta `INICIAR_CON_CONSOLA.bat`.

El programa dibuja esquemas eléctricos; no realiza simulación ni certificación de seguridad. La librería Pillow es opcional para determinados recursos de imagen.

## Contenido

- `electrical_work.py`: aplicación gráfica principal.
- `core.py`, `symbology.py`: modelo y símbolos.
- `documentation.py`, `page_layout.py`, `pdf_export.py`: documentación, páginas e impresión.
- `INICIAR_WINDOWS.bat`, `INICIAR_CON_CONSOLA.bat`: arranque Windows.
- `CAMBIOS_V0_38_3.txt`, `LEEME.txt`: documentación de la versión.

## Protección de datos

Esta copia de GitHub **no incluye proyectos de usuario ni ejemplos construidos sobre un trabajo personal**. En particular, se han excluido el proyecto `.ework` y el PDF de ejemplo que figuraban en la entrega original. Los trabajos reales y sus copias de seguridad deben conservarse fuera del repositorio. `.gitignore` no impide subir un archivo manualmente mediante la interfaz web de GitHub: comprueba siempre la lista antes de confirmar.

## Evolución

- Rama objetivo: `main`.
- Esta versión no se sustituirá por Compacto V0.4 hasta que el usuario autorice expresamente el cambio de versión de trabajo.
- La línea experimental se conserva en otra rama: `desarrollo-compacto`.
