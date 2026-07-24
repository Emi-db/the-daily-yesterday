// ============================================================
//  EL BUSCADOR DEL ARCHIVO — The Daily Yesterday
//  Vive en archivo.html. Busca dentro de TODO el texto de las
//  crónicas (título, bajada, cuerpo, lugar, fecha...) sin
//  distinguir mayúsculas ni acentos: "peron" encuentra "Perón".
//  La búsqueda queda escrita en la dirección (?q=palabra), así
//  que un enlace de búsqueda se puede compartir o guardar.
// ============================================================

// noticias.js se carga antes que este archivo, así que acá
// EVENTOS ya existe. Lo ordenamos por fecha, igual que la portada.
EVENTOS.sort((a, b) => a.fecha.localeCompare(b.fecha));

const MESES_BUSCADOR = ["enero","febrero","marzo","abril","mayo","junio",
                        "julio","agosto","septiembre","octubre","noviembre","diciembre"];

// "1816-07-09" -> "9 de julio de 1816"
function fechaLegible(fechaISO) {
  const [a, m, d] = fechaISO.split("-");
  return `${parseInt(d)} de ${MESES_BUSCADOR[parseInt(m) - 1]} de ${parseInt(a)}`;
}

// Las crónicas anteriores a Cristo llevan el campo opcional "aC"
// (su fecha interna usa el año 0000 para ordenar bien). Esta
// función muestra el año verdadero: "15 de marzo de 44 a. C."
function fechaDeEvento(ev) {
  if (!ev.aC) return fechaLegible(ev.fecha);
  const [a, m, d] = ev.fecha.split("-");
  return `${parseInt(d)} de ${MESES_BUSCADOR[parseInt(m) - 1]} de ${ev.aC} a. C.`;
}

// ------------------------------------------------------------
// Normalizar: todo a minúsculas y sin tildes. El truco:
// normalize("NFD") separa "é" en "e" + tilde suelta, y el
// replace borra esas tildes sueltas (Unicode las guarda todas
// entre los códigos 0300 y 036F). Queda la "e" pelada.
// ------------------------------------------------------------
function normalizar(texto) {
  return texto.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

// ------------------------------------------------------------
// El índice: TODO el texto de cada crónica pegado en una sola
// tira, ya normalizado. Se arma UNA vez al cargar la página;
// después cada búsqueda es solo recorrer estas 90 tiras, que
// para una computadora es instantáneo.
// ------------------------------------------------------------
const INDICE = EVENTOS.map(ev => {
  const partes = [ev.fecha, fechaDeEvento(ev), ev.corto, ev.volanta,
                  ev.titulo, ev.bajada, ev.lugar, ev.cuerpo.join(" ")];
  if (ev.secuela) {
    partes.push(ev.secuela.titulo, ev.secuela.lugar, ev.secuela.cuerpo.join(" "));
  }
  return normalizar(partes.join(" "));
});

// Busca las crónicas donde aparecen TODAS las palabras pedidas.
// Devuelve las palabras normalizadas (para resaltar después) y
// las crónicas halladas.
function buscar(consulta) {
  const palabras = normalizar(consulta).split(/\s+/).filter(Boolean);
  const halladas = [];
  EVENTOS.forEach((ev, i) => {
    if (palabras.every(p => INDICE[i].includes(p))) halladas.push(ev);
  });
  return { palabras, halladas };
}

// ------------------------------------------------------------
// Resaltar: para pintar la palabra en el texto ORIGINAL (que
// tiene tildes) armamos un "regex" donde cada letra acepta sus
// variantes: buscar "peron" pinta "Perón" porque la o acepta ó.
// ------------------------------------------------------------
const VARIANTES = { a: "[aáà]", e: "[eéè]", i: "[ií]", o: "[oó]", u: "[uúü]", n: "[nñ]", c: "[cç]" };

function regexDePalabra(palabra) {
  const patron = palabra.split("").map(letra =>
    VARIANTES[letra] || letra.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")  // escapar símbolos raros
  ).join("");
  return new RegExp(patron, "gi");  // g = todas las veces, i = sin distinguir mayúsculas
}

function resaltar(texto, palabras) {
  // Primero marcamos los hallazgos con dos caracteres "imposibles"
  // (los códigos 1 y 2 no aparecen en ningún texto normal) y al
  // final los cambiamos por <mark>. Si pusiéramos <mark> directo,
  // la segunda palabra podría encontrarse a sí misma dentro de
  // la etiqueta recién insertada y romper el HTML.
  let resultado = texto;
  palabras.forEach(p => {
    resultado = resultado.replace(regexDePalabra(p), m => "\u0001" + m + "\u0002");
  });
  return resultado.split("\u0001").join("<mark>").split("\u0002").join("</mark>");
}

// ------------------------------------------------------------
// El extracto: el pedacito de crónica alrededor de la primera
// aparición de la palabra, cortado en bordes de palabra.
// ------------------------------------------------------------
function extracto(ev, palabras) {
  const campos = [ev.cuerpo.join(" "), ev.bajada, ev.volanta];
  for (const texto of campos) {
    const donde = normalizar(texto).indexOf(palabras[0]);
    if (donde !== -1) {
      const desde = Math.max(0, donde - 55);
      const hasta = Math.min(texto.length, donde + 130);
      let trozo = texto.slice(desde, hasta);
      // recortar hasta el primer/último espacio para no partir palabras
      if (desde > 0) trozo = "…" + trozo.slice(trozo.indexOf(" ") + 1);
      if (hasta < texto.length) trozo = trozo.slice(0, trozo.lastIndexOf(" ")) + "…";
      return resaltar(trozo, palabras);
    }
  }
  return resaltar(ev.bajada, palabras);  // si no, mostramos la bajada
}

// Lo que escribe el visitante se muestra de vuelta en la página:
// hay que "desactivar" los símbolos de HTML para que nadie pueda
// inyectar código con un enlace ?q=<script>... (seguridad básica).
function escaparHTML(texto) {
  return texto.replace(/&/g, "&amp;").replace(/</g, "&lt;")
              .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ------------------------------------------------------------
// Dibujar los resultados (y esconder el índice mientras tanto)
// ------------------------------------------------------------
const campoBusqueda = document.getElementById("campo-archivo");
const zonaResultados = document.getElementById("zona-resultados");
const indiceArchivo = document.getElementById("indice-archivo");

function mostrarResultados(consulta) {
  const { palabras, halladas } = buscar(consulta);
  const consultaSegura = escaparHTML(consulta);

  // Avisamos a Google Analytics qué se buscó (dato anónimo):
  // sirve para saber qué le interesa a la gente.
  if (typeof gtag === "function") gtag("event", "search", { search_term: consulta });

  const volver = `<a href="#" id="limpiar-busqueda">ver el índice completo ✕</a>`;
  let contenido;

  if (halladas.length === 0) {
    contenido = `<p class="aviso-resultados">Nuestros archivistas revisaron las
      ${EVENTOS.length} ediciones y no hallaron mención de «${consultaSegura}».
      Pruebe con otra palabra: un apellido, una ciudad, un año. — ${volver}</p>`;
  } else {
    const plural = halladas.length === 1 ? "crónica hallada" : "crónicas halladas";
    const filas = halladas.map(ev => `
      <li class="resultado">
        <a href="notas/${ev.fecha}.html">
          <span class="fecha-res">${fechaDeEvento(ev)} — ${escaparHTML(ev.lugar)}</span>
          <b>${resaltar(ev.titulo, palabras)}</b>
        </a>
        <p class="extracto">${extracto(ev, palabras)}</p>
      </li>`).join("");
    contenido = `<p class="aviso-resultados">${halladas.length} ${plural} para
      «${consultaSegura}» — ${volver}</p>
      <ul class="resultados">${filas}</ul>`;
  }

  zonaResultados.innerHTML = contenido;
  indiceArchivo.style.display = "none";  // el índice se aparta mientras se busca

  document.getElementById("limpiar-busqueda").addEventListener("click", e => {
    e.preventDefault();
    limpiarBusqueda();
  });
}

function limpiarBusqueda() {
  zonaResultados.innerHTML = "";
  indiceArchivo.style.display = "";
  campoBusqueda.value = "";
  // borrar el "?q=..." de la dirección sin recargar la página
  history.replaceState(null, "", location.pathname);
  campoBusqueda.focus();
}

// ------------------------------------------------------------
// Los dos caminos de entrada:
// 1) el formulario de esta página (buscar sin recargar)
// 2) llegar con ?q=palabra en la dirección (desde la portada
//    o desde un enlace compartido)
// ------------------------------------------------------------
document.getElementById("buscador-archivo").addEventListener("submit", e => {
  e.preventDefault();  // que el formulario no recargue la página
  const consulta = campoBusqueda.value.trim();
  if (!consulta) return limpiarBusqueda();
  // escribimos la búsqueda en la dirección, para poder compartirla
  history.replaceState(null, "", "?q=" + encodeURIComponent(consulta));
  mostrarResultados(consulta);
});

const consultaInicial = new URLSearchParams(location.search).get("q");
if (consultaInicial) {
  campoBusqueda.value = consultaInicial;
  mostrarResultados(consultaInicial);
}
