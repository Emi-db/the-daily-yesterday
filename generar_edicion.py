# ============================================================
#  THE DAILY YESTERDAY — generador de la edición del día
# ============================================================
#  Este script es "la imprenta" del diario: se corre una vez por
#  día (a mano o con la tarea programada) y hace lo siguiente:
#
#    1. Baja los RSS de varios medios argentinos, por sección.
#       (RSS = un archivo XML que los diarios publican justamente
#       para que otros programas lean sus titulares)
#    2. De cada nota se queda con: titular, resumen corto, link
#       y nombre del medio. NUNCA el texto completo: somos un
#       agregador, el lector va al medio a leer la nota.
#    3. Descarta titulares repetidos entre medios.
#    4. Escribe todo en "edicion.js", que es lo que la página
#       hoy.html carga y muestra.
#
#  Se corre así:   python generar_edicion.py
#  No necesita instalar nada: usa solo lo que trae Python.
# ============================================================

import html
import io
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# ------------------------------------------------------------
# CONFIGURACIÓN: las secciones y sus fuentes RSS.
# Para agregar un medio: sumás una tupla ("Nombre", "url del rss")
# a la sección que corresponda. Si un feed falla, no pasa nada:
# el script sigue con los demás.
# ------------------------------------------------------------
SECCIONES = [
    ("El País", [
        ("Clarín",     "https://www.clarin.com/rss/politica/"),
        ("La Nación",  "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/politica/?outputType=xml"),
        ("Infobae",    "https://www.infobae.com/arc/outboundfeeds/rss/category/politica/?outputType=xml"),
    ]),
    ("Economía", [
        ("Clarín",     "https://www.clarin.com/rss/economia/"),
        ("La Nación",  "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/?outputType=xml"),
        ("Ámbito",     "https://www.ambito.com/rss/economia.xml"),
    ]),
    ("El Mundo", [
        ("Clarín",     "https://www.clarin.com/rss/mundo/"),
        ("La Nación",  "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/el-mundo/?outputType=xml"),
        ("Infobae",    "https://www.infobae.com/arc/outboundfeeds/rss/category/mundo/?outputType=xml"),
    ]),
    ("Deportes", [
        ("Clarín",     "https://www.clarin.com/rss/deportes/"),
        ("La Nación",  "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/deportes/?outputType=xml"),
        ("Olé",        "https://www.ole.com.ar/rss/"),
    ]),
]

NOTAS_POR_SECCION = 5      # cuántas notas mostramos por sección
LARGO_RESUMEN = 240        # letras máximas del resumen

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_EN = ["January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"]

# ------------------------------------------------------------
# LA EDICIÓN INTERNACIONAL, en dos idiomas: mismos criterios,
# fuentes distintas. No traducimos nada: elegimos medios que ya
# escriben en cada idioma.
# ------------------------------------------------------------
SECCIONES_MUNDO_ES = [
    ("El Mundo", [
        ("BBC Mundo",  "https://feeds.bbci.co.uk/mundo/rss.xml"),
        ("El País",    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada"),
        ("France 24",  "https://www.france24.com/es/rss"),
    ]),
    ("Economía", [
        ("El País",    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada"),
        ("Expansión",  "https://e00-expansion.uecdn.es/rss/portada.xml"),
    ]),
    ("Ciencia y Tecnología", [
        ("El País",    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada"),
        ("El País",    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada"),
    ]),
    ("Deportes", [
        ("Marca",           "https://e00-marca.uecdn.es/rss/portada.xml"),
        ("Mundo Deportivo", "https://www.mundodeportivo.com/rss/home.xml"),
    ]),
]

SECCIONES_MUNDO_EN = [
    ("World", [
        ("BBC",           "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("The Guardian",  "https://www.theguardian.com/world/rss"),
        ("N.Y. Times",    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ]),
    ("Business", [
        ("BBC",           "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("The Guardian",  "https://www.theguardian.com/business/rss"),
        ("N.Y. Times",    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ]),
    ("Science & Tech", [
        ("BBC",           "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
        ("The Guardian",  "https://www.theguardian.com/science/rss"),
        ("N.Y. Times",    "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml"),
    ]),
    ("Sports", [
        ("BBC",           "https://feeds.bbci.co.uk/sport/rss.xml"),
        ("The Guardian",  "https://www.theguardian.com/sport/rss"),
    ]),
]

CARPETA = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (compatible; TheDailyYesterday/1.0; agregador personal, muestra titular+resumen+link)"}


# ------------------------------------------------------------
# PASO 1: bajar y leer un feed RSS
# ------------------------------------------------------------
def bajar_feed(url):
    """Baja el XML de un RSS y devuelve la lista de sus notas."""
    pedido = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(pedido, timeout=25) as respuesta:
        xml_crudo = respuesta.read()

    raiz = ET.fromstring(xml_crudo)

    # Un RSS clásico es: <rss><channel><item>...</item>... El
    # ".//" busca en cualquier nivel, por si el feed es raro.
    notas = []
    for item in raiz.iter("item"):
        titulo = texto_de(item, "title")
        link = texto_de(item, "link")
        descripcion = texto_de(item, "description")
        if titulo and link:
            notas.append({
                "titulo": limpiar(titulo),
                "link": link.strip(),
                "resumen": recortar(limpiar(descripcion)),
            })
    return notas


def texto_de(item, etiqueta):
    """Saca el texto de una sub-etiqueta del item (o cadena vacía)."""
    elemento = item.find(etiqueta)
    return (elemento.text or "") if elemento is not None else ""


def limpiar(texto):
    """Saca las etiquetas HTML y los espacios repetidos."""
    texto = html.unescape(texto)                # &aacute; -> á
    texto = re.sub(r"<[^>]+>", " ", texto)      # <b>...</b> -> afuera
    texto = re.sub(r"\s+", " ", texto).strip()  # espacios dobles -> uno
    return texto


def recortar(texto):
    """Corta el resumen en ~240 letras sin partir una palabra."""
    if len(texto) <= LARGO_RESUMEN:
        return texto
    corte = texto[:LARGO_RESUMEN - 1]
    corte = re.sub(r"\s+\S*$", "", corte)       # saca la palabra a medias
    return corte + "…"


# ------------------------------------------------------------
# PASO 2: detectar titulares repetidos entre medios
# (si dos titulares comparten muchas palabras, son la misma
#  noticia contada por dos diarios: nos quedamos con la primera)
# ------------------------------------------------------------
def palabras_clave(titulo):
    """Las palabras 'importantes' del titular (largas, en minúscula)."""
    return set(p for p in re.findall(r"\w+", titulo.lower()) if len(p) > 3)


def es_repetida(titulo, ya_elegidas):
    nuevas = palabras_clave(titulo)
    if not nuevas:
        return False
    for otro in ya_elegidas:
        comunes = nuevas & palabras_clave(otro)
        # si comparten más de la mitad de las palabras, es la misma
        if len(comunes) >= len(nuevas) / 2 and len(comunes) >= 3:
            return True
    return False


# ------------------------------------------------------------
# PASO 3: armar cada sección mezclando los medios
# ------------------------------------------------------------
def armar_seccion(nombre, fuentes, titulos_vistos):
    """Toma notas de cada medio 'por turnos' hasta llenar la sección.

    "titulos_vistos" es UNA SOLA lista compartida por todas las
    secciones de la edición: así una noticia que ya salió en
    "El País" no vuelve a aparecer en "Economía" aunque otro
    medio la tenga en esa sección.
    """
    canastas = []       # una lista de notas por cada medio
    for medio, url in fuentes:
        try:
            notas = bajar_feed(url)
            for n in notas:
                n["fuente"] = medio
            canastas.append(notas)
            print(f"   {medio:16} OK ({len(notas)} notas)")
        except Exception as error:
            print(f"   {medio:16} FALLÓ: {type(error).__name__}")

    # "Por turnos": 1ª de Clarín, 1ª de La Nación, 1ª de Infobae,
    # 2ª de Clarín... así ningún medio domina la sección.
    elegidas = []
    ronda = 0
    while len(elegidas) < NOTAS_POR_SECCION and ronda < 10:
        hubo_algo = False
        for canasta in canastas:
            if ronda < len(canasta):
                hubo_algo = True
                nota = canasta[ronda]
                if not es_repetida(nota["titulo"], titulos_vistos):
                    elegidas.append(nota)
                    titulos_vistos.append(nota["titulo"])
                    if len(elegidas) == NOTAS_POR_SECCION:
                        break
        if not hubo_algo:
            break
        ronda += 1

    return {"nombre": nombre, "notas": elegidas}


def generar_edicion(configuracion, fecha_texto, hora):
    """Arma una edición completa (todas sus secciones) con un
    único filtro de repetidas compartido entre secciones."""
    titulos_vistos = []
    secciones = []
    for nombre, fuentes in configuracion:
        print(f"» {nombre}")
        seccion = armar_seccion(nombre, fuentes, titulos_vistos)
        if seccion["notas"]:
            secciones.append(seccion)
    return {"fecha": fecha_texto, "generada": hora, "secciones": secciones}


# ------------------------------------------------------------
# PASO 4: escribir edicion.js
# ------------------------------------------------------------
def escribir_js(nombre_archivo, nombre_variable, datos):
    """Escribe los datos como un .js cargable con <script>.
    json.dumps convierte el diccionario de Python en texto JSON;
    le anteponemos "const X =" y ya es JavaScript válido (así la
    página lo carga sin problemas de CORS ni de fetch)."""
    contenido = "// Archivo GENERADO por generar_edicion.py — no editar a mano.\n"
    contenido += f"const {nombre_variable} = " + json.dumps(datos, ensure_ascii=False, indent=2) + ";\n"
    with io.open(os.path.join(CARPETA, nombre_archivo), "w", encoding="utf-8") as f:
        f.write(contenido)


def contar(edicion):
    return sum(len(s["notas"]) for s in edicion["secciones"])


def main():
    ahora = datetime.now()
    hora = ahora.strftime("%H:%M")
    fecha_es = f"{ahora.day} de {MESES[ahora.month - 1]} de {ahora.year}"
    fecha_en = f"{MESES_EN[ahora.month - 1]} {ahora.day}, {ahora.year}"

    # ---- 1) La edición nacional ----
    print(f"Imprimiendo la edición del {ahora.strftime('%d/%m/%Y %H:%M')}...")
    nacional = generar_edicion(SECCIONES, fecha_es, hora)
    escribir_js("edicion.js", "EDICION", nacional)
    print(f"Nacional: {contar(nacional)} notas -> edicion.js\n")

    # ---- 2) La edición internacional, en los dos idiomas ----
    print("=== Edición internacional (español) ===")
    mundo_es = generar_edicion(SECCIONES_MUNDO_ES, fecha_es, hora)
    print("=== World edition (English) ===")
    mundo_en = generar_edicion(SECCIONES_MUNDO_EN, fecha_en, hora)

    escribir_js("edicion_mundo.js", "EDICION_MUNDO", {"es": mundo_es, "en": mundo_en})
    print(f"Internacional: {contar(mundo_es)} notas (es) + {contar(mundo_en)} notas (en) -> edicion_mundo.js")


if __name__ == "__main__":
    main()
