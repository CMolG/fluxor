"""Detects Spanish lines, so the repository stays in American English.

The one detector: this catalog's `validate` uses it, and so does the harness hook of the project
that hosts the catalog (its `no_spanish.py` imports this module and keeps only its own exemptions),
so the two can never disagree about what counts as Spanish. Three signals, from strongest to
weakest: characters English never uses, two or more Spanish stopwords (or one with an acute `é`,
which English borrows only in words like `café`), and whole identifier tokens that are Spanish
words.

A line that must stay Spanish outside the functional-data globs carries the marker `lang:es` in a
comment on the same line. It is greppable on purpose: an exception nobody can list is not one.
"""

from __future__ import annotations

import re

STRONG = re.compile(r"[ñÑ¿¡áíóúÁÍÓÚ]")
SOFT = re.compile(r"[éÉ]")
# `todo`, `el`, `solo`, `son`, `sin`, `sea` and `hay` are left out: TODO comments, `el` for an
# element, Math.sin and English words would fire on every other file.
STOPWORDS = frozenset(
    """que para los las del una unas unos con por pero como esta este estos estas cuando porque
    tiene tienen hace hacen desde sobre entre hasta donde muy tambien nunca siempre aqui ahora cada
    otra otro otros otras puede pueden debe deben esto eso asi mismo misma fue sus nos les""".split()
)
# Exact whole tokens after splitting camelCase, snake_case and kebab-case. Never prefixes: a prefix
# list reads `final`, `find` and `pagination` as Spanish. Words that are also English (`anterior`,
# `final`, `real`) are deliberately absent.
TOKENS = frozenset(
    """nombre nombres comando comandos recurso recursos prueba pruebas atestado huella huellas salida
    salidas entrada entradas sello arbol limpio codigo tarjeta tarjetas motivo afectadas afectada
    lectura lecturas pendiente pendientes trozos hilos compilar escribir construir construido
    construidos paquete paquetes navegador navegadores descendientes resuelto resueltos catalogo
    declarado proyecto proyectos seccion secciones ejecutar informar lanzar terminar inicio
    estimacion duracion duraciones servicio servicios aviso avisos despliegue fecha fichero ficheros
    carpeta tanda limpieza preparar guardar cargar mostrar ocultar abrir cerrar cuenta usuario
    usuarios texto titulo boton pagina paginas mensaje mensajes rojo gris raiz rama chocan vivos
    hijo hijos vacio valores resultado resultados tiempo segundos minutos horas dias semana linea
    lineas fila filas columna columnas tabla tablas clave claves lista listas errores ruta rutas
    estado estados puerto puertos tipo tipos colision colisiones unitaria unitarias justificar rojos
    vigilados vigiladas barrido sesion enlace enlaces descripcion precio precios correo ajustes
    buscar busqueda nuevo nueva nuevos nuevas enviar publicar publicado ultimo ultima primero
    primera siguiente borrar borrado crear creado actualizar ejemplo ejemplos""".split()
)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
PARTS = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])")
WORD = re.compile(r"[a-záéíóúñü]+")
# A path or URL names something that exists; its tokens are not prose.
PATHLIKE = re.compile(r"(?:[a-z]+://)?[\w.@~-]*/[\w./@~-]*")
MARKER = "lang:es"


def spanish_tokens(text: str) -> list[str]:
    return [p for ident in IDENT.findall(text) for p in (PARTS.findall(ident) or [ident]) if p.lower() in TOKENS]


def spanish_name(path: str) -> bool:
    """A new file's own name: `pruebas-nuevas.mjs` is Spanish even if its content is not."""
    return bool(spanish_tokens(path.rsplit("/", 1)[-1]))


def is_spanish(line: str) -> bool:
    if MARKER in line:
        return False
    if STRONG.search(line):
        return True
    stops = set(WORD.findall(line.lower())) & STOPWORDS
    if len(stops) >= 2 or (stops and SOFT.search(line)):
        return True
    return bool(spanish_tokens(PATHLIKE.sub(" ", line)))
