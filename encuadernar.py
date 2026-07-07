# ============================================================
#  EL ENCUADERNADOR — The Daily Yesterday
#  Lee noticias.js y genera:
#    · notas/<fecha>.html  (una página real por crónica, para
#      Google y para compartir enlaces directos)
#    · archivo.html        (índice de todas las crónicas)
#    · creditos.html       (autores y licencias de los grabados,
#      leídos de img/fuentes.json)
#    · sitemap.xml         (la lista de páginas para Google)
#    · robots.txt
#  Correr de nuevo cada vez que se agregan crónicas:
#    python encuadernar.py
# ============================================================
import json, os, re, html

CARPETA = os.path.dirname(os.path.abspath(__file__))
DOMINIO = "https://thedailyyesterday.com"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# ------------------------------------------------------------
# 1) Leer noticias.js (es JavaScript: lo convertimos a JSON
#    con tres retoques y lo carga json.loads)
# ------------------------------------------------------------
def leer_eventos():
    with open(os.path.join(CARPETA, "noticias.js"), encoding="utf-8") as f:
        texto = f.read()
    # afuera los comentarios (líneas que empiezan con //)
    texto = "\n".join(l for l in texto.split("\n") if not l.strip().startswith("//"))
    # "const EVENTOS = [ ... ];"  ->  "[ ... ]"
    texto = texto[texto.index("["): texto.rindex("]") + 1]
    # claves sin comillas -> claves con comillas: fecha: -> "fecha":
    texto = re.sub(r'^(\s*)([a-zA-Z_]\w*)\s*:', r'\1"\2":', texto, flags=re.M)
    # comas colgantes antes de } o ] (JS las perdona, JSON no)
    texto = re.sub(r",(\s*[}\]])", r"\1", texto)
    eventos = json.loads(texto)
    eventos.sort(key=lambda e: e["fecha"])
    return eventos

def fecha_larga(fecha_iso):
    a, m, d = fecha_iso.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {int(a)}"

def esc(t):
    """Para poner texto dentro de atributos HTML sin sorpresas."""
    return html.escape(t, quote=True)

def leer_fuentes():
    ruta = os.path.join(CARPETA, "img", "fuentes.json")
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    return {}

# ------------------------------------------------------------
# 2) La cáscara de página compartida (cabezal + pie del diario)
# ------------------------------------------------------------
def pagina(titulo, meta, cuerpo, raiz=""):
    """Envuelve un contenido en la hoja del diario.
    raiz = "" para páginas en la raíz, "../" para las de notas/."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(titulo)}</title>
{meta}<link rel="icon" href="{raiz}favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Playfair+Display:ital,wght@0,700;0,900;1,600&family=Old+Standard+TT:ital@0;1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{raiz}estilos.css">
</head>
<body>

<div class="hoja">

  <header class="cabezal">
    <div class="fila-superior">
      <span>Fundado en el porvenir</span>
      <span>Precio: dos reales</span>
    </div>
    <h1 onclick="location.href='{raiz}index.html'" title="Ir a la portada">The Daily Yesterday</h1>
    <p class="lema">« Todas las noticias de todos los ayeres »</p>
    <div class="filete-doble"></div>
    <nav class="cintillo">
      <a href="{raiz}index.html">El Archivo Histórico</a>
      <span class="sep">·</span>
      <a href="{raiz}hoy.html">La Edición de Hoy</a>
      <span class="sep">·</span>
      <a href="{raiz}mundo.html">El Mundo</a>
    </nav>
{cuerpo}
  <footer>
    The Daily Yesterday — crónicas escritas como si el diario hubiera estado ahí.
    Los hechos son históricos; la redacción, de época imaginada.<br>
    <a href="{raiz}archivo.html">Índice del archivo</a> ·
    <a href="{raiz}creditos.html">Créditos de los grabados</a> ·
    <a href="{raiz}privacidad.html">Privacidad</a>
  </footer>

</div>

</body>
</html>
"""

# Ojo: pagina() deja el <header> abierto a propósito. Cada
# "cuerpo" empieza con linea_edicion(), que agrega la línea de
# edición propia de esa página y recién ahí cierra el </header>.

def linea_edicion(izquierda, derecha):
    return f"""    <div class="linea-edicion">
      <span id="edicion-numero">{izquierda}</span>
      <span id="edicion-fecha">{derecha}</span>
    </div>
  </header>
"""

# ------------------------------------------------------------
# 3) Una página por crónica
# ------------------------------------------------------------
def generar_notas(eventos, fuentes):
    os.makedirs(os.path.join(CARPETA, "notas"), exist_ok=True)
    total = len(eventos)

    for i, ev in enumerate(eventos):
        fecha = ev["fecha"]
        url = f"{DOMINIO}/notas/{fecha}.html"

        # --- metadatos para Google y para compartir ---
        meta = f"""<meta name="description" content="{esc(ev['bajada'])}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="The Daily Yesterday">
<meta property="og:title" content="{esc(ev['titulo'])}">
<meta property="og:description" content="{esc(ev['bajada'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{DOMINIO}/img/{fecha}.jpg">
<meta name="twitter:card" content="summary_large_image">
"""
        # --- el grabado, con su crédito de autor si lo tenemos ---
        fu = fuentes.get(fecha, {})
        if fu.get("verificado") and fu.get("autor"):
            credito = f"{ev['corto']} — {fu['autor']} · {fu.get('licencia', '')} (Wikimedia Commons)"
        else:
            credito = f"{ev['corto']} — de los archivos ilustrados de este diario (Wikimedia Commons)"

        parrafos = "".join(f"      <p>{p}</p>\n" for p in ev["cuerpo"])

        secuela_html = ""
        if "secuela" in ev:
            s = ev["secuela"]
            sec_parrafos = "".join(f"        <p>{p}</p>\n" for p in s["cuerpo"])
            secuela_html = f"""      <aside class="secuela">
        <div class="marbete">La historia continuó</div>
        <h3>{s['titulo']}</h3>
        <div class="dateline">{s['lugar']}, {fecha_larga(s['fecha'])}</div>
{sec_parrafos}      </aside>
"""
        # --- navegación entre crónicas (anterior / siguiente) ---
        nav = []
        if i > 0:
            ant = eventos[i - 1]
            nav.append(f'<a href="{ant["fecha"]}.html">◂ {ant["fecha"][:4]} · {ant["corto"]}</a>')
        nav.append(f'<a href="../archivo.html">El Archivo</a>')
        if i < total - 1:
            sig = eventos[i + 1]
            nav.append(f'<a href="{sig["fecha"]}.html">{sig["fecha"][:4]} · {sig["corto"]} ▸</a>')
        nav_html = " &nbsp;·&nbsp; ".join(nav)

        cuerpo = linea_edicion(
            f'<a href="../index.html">◂ Portada</a> &nbsp;·&nbsp; Edición N.º {i + 1} de {total}',
            fecha_larga(fecha),
        ) + f"""
  <main class="nota">
    <div class="volanta">{ev['volanta']}</div>
    <h2>{ev['titulo']}</h2>
    <p class="bajada">{ev['bajada']}</p>
    <div class="dateline">{ev['lugar']}, {fecha_larga(fecha)}</div>
    <figure class="grabado">
      <img src="../img/{fecha}.jpg" alt="{esc(ev['corto'])}"
           onerror="this.parentElement.style.display='none'">
      <figcaption>{credito}</figcaption>
    </figure>
    <div class="cuerpo">
{parrafos}    </div>
{secuela_html}    <div class="fin-nota">❦</div>
    <nav class="nav-notas" style="text-align:center; margin-top:1.5rem; font-style:italic">
      {nav_html}
    </nav>
  </main>
"""
        with open(os.path.join(CARPETA, "notas", f"{fecha}.html"), "w", encoding="utf-8") as f:
            f.write(pagina(f"{ev['titulo']} — The Daily Yesterday", meta, cuerpo, raiz="../"))

    print(f"notas/: {total} paginas")

# ------------------------------------------------------------
# 4) El índice del archivo (una página estática con todo)
# ------------------------------------------------------------
def generar_archivo(eventos):
    decadas = {}
    for ev in eventos:
        d = int(ev["fecha"][:4]) // 10 * 10
        decadas.setdefault(d, []).append(ev)

    secciones = ""
    for d in sorted(decadas):
        filas = "".join(
            f'      <li><a href="notas/{ev["fecha"]}.html">'
            f'<b>{fecha_larga(ev["fecha"])}</b> — {ev["corto"]}</a><br>'
            f'<span style="font-style:italic">{ev["titulo"]}</span></li>\n'
            for ev in decadas[d]
        )
        secciones += f"""    <section style="margin-bottom:1.4rem">
      <div class="titulo-seccion">Década de {d}</div>
      <ul style="list-style:none; padding:0; line-height:1.5">
{filas}      </ul>
    </section>
"""
    meta = f"""<meta name="description" content="Todas las crónicas históricas de The Daily Yesterday, de 1347 a 2022, escritas como si el diario hubiera estado ahí.">
<link rel="canonical" href="{DOMINIO}/archivo.html">
"""
    cuerpo = linea_edicion("El Archivo completo", f"{len(eventos)} ediciones") + f"""
  <main class="nota">
    <h2 style="text-align:center">Todas las ediciones del archivo</h2>
    <p class="bajada" style="text-align:center">De la peste de 1347 a la tercera estrella de 2022.</p>
{secciones}  </main>
"""
    with open(os.path.join(CARPETA, "archivo.html"), "w", encoding="utf-8") as f:
        f.write(pagina("El Archivo — The Daily Yesterday", meta, cuerpo))
    print("archivo.html: listo")

# ------------------------------------------------------------
# 5) Créditos de los grabados
# ------------------------------------------------------------
def generar_creditos(eventos, fuentes):
    por_fecha = {ev["fecha"]: ev for ev in eventos}
    filas = ""
    pendientes = 0
    for fecha in sorted(fuentes):
        fu = fuentes[fecha]
        ev = por_fecha.get(fecha, {})
        corto = ev.get("corto", fecha)
        if fu.get("verificado"):
            lic = fu.get("licencia", "")
            lic_html = (f'<a href="{esc(fu["licencia_url"])}" rel="license">{esc(lic)}</a>'
                        if fu.get("licencia_url") else esc(lic))
            filas += f"""      <li style="margin-bottom:.7rem">
        <a href="notas/{fecha}.html"><b>{fecha_larga(fecha)} — {corto}</b></a><br>
        <a href="{esc(fu.get('pagina', ''))}">{esc(fu.get('archivo', ''))}</a><br>
        Autor: {esc(fu.get('autor', 'no consignado'))} · Licencia: {lic_html}
      </li>
"""
        else:
            pendientes += 1
            filas += f"""      <li style="margin-bottom:.7rem">
        <b>{fecha_larga(fecha)} — {corto}</b><br>
        Fuente en verificación (Wikimedia Commons).
      </li>
"""
    aviso = ("" if not fuentes else
             f"<p class='bajada'>Los grabados de este diario provienen de Wikimedia Commons: "
             f"obras de dominio público o con licencias libres que exigen —con justicia— "
             f"nombrar a sus autores. Aquí están, uno por uno.</p>")
    meta = f"""<meta name="description" content="Autores y licencias de las imágenes de The Daily Yesterday.">
<link rel="canonical" href="{DOMINIO}/creditos.html">
"""
    cuerpo = linea_edicion("Créditos de los grabados", f"{len(fuentes)} imágenes") + f"""
  <main class="nota">
    <h2 style="text-align:center">Los grabados y sus autores</h2>
    {aviso}
    <ul style="list-style:none; padding:0; line-height:1.45; font-size:.95em">
{filas}    </ul>
  </main>
"""
    with open(os.path.join(CARPETA, "creditos.html"), "w", encoding="utf-8") as f:
        f.write(pagina("Créditos — The Daily Yesterday", meta, cuerpo))
    print(f"creditos.html: {len(fuentes)} imagenes ({pendientes} pendientes)")

# ------------------------------------------------------------
# 6) sitemap.xml y robots.txt
# ------------------------------------------------------------
def generar_sitemap(eventos):
    urls = [f"{DOMINIO}/", f"{DOMINIO}/hoy.html", f"{DOMINIO}/mundo.html",
            f"{DOMINIO}/archivo.html", f"{DOMINIO}/creditos.html"]
    urls += [f"{DOMINIO}/notas/{ev['fecha']}.html" for ev in eventos]
    cuerpo = "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
    with open(os.path.join(CARPETA, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{cuerpo}</urlset>\n')
    with open(os.path.join(CARPETA, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {DOMINIO}/sitemap.xml\n")
    print(f"sitemap.xml: {len(urls)} URLs · robots.txt: listo")

# ------------------------------------------------------------
if __name__ == "__main__":
    eventos = leer_eventos()
    fuentes = leer_fuentes()
    print(f"noticias.js: {len(eventos)} cronicas leidas")
    generar_notas(eventos, fuentes)
    generar_archivo(eventos)
    generar_creditos(eventos, fuentes)
    generar_sitemap(eventos)
    print("Encuadernado completo.")
