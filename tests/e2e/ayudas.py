"""Ayudas comunes de las pruebas en navegador.

Sin desplazamiento (decisión 0005): lo que no cabe está en otra pantalla de la misma página
y se llega con «Anterior / Siguiente», como haría una persona.

Encuadre (decisión 0007): `revisar` comprueba en una sola llamada axe, que no hay
desplazamiento, que nada se sale de la pantalla ni de su caja, que ningún botón tapa a otro,
que los elementos de una lista no se montan, que los objetivos miden 48 px o más y, con el
peor perfil, que la letra crece.
"""

from axe_playwright_python.sync_playwright import Axe

# Tamaños de revisión (decisión 0005 + móviles reales del acta del 19/11): el alto de los dos
# móviles es el que queda con las barras del navegador abiertas.
RESOLUCIONES = {
    "movil-360": (360, 640),
    "iphone-15-safari": (393, 659),
    "android-chrome": (412, 780),
    "tablet-horizontal": (1024, 768),
    "tablet-grande": (1280, 800),
    "ordenador": (1366, 768),
}
MOVILES = ["movil-360", "iphone-15-safari", "android-chrome"]
ETIQUETAS_WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
# El peor perfil de los datos de prueba: Sofía (letra 32, botones 80, alto contraste).
PEOR_PERFIL = "A03"


def con_sesion(page, live_server, client, usuario):
    """Entra como `usuario` sin pasar por el formulario: la cookie de sesión al navegador."""
    client.force_login(usuario)
    page.context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )


def sin_errores_axe(page):
    resultado = Axe().run(page, options={"runOnly": {"type": "tag", "values": ETIQUETAS_WCAG}})
    assert resultado.violations_count == 0, resultado.generate_report()


_ENCUADRE = """({letra}) => {
  const vw = innerWidth, vh = innerHeight;
  // Lo que se ve: ni oculto ni «solo para el lector de pantalla» (1×1 px recortado).
  const oculto = (el) => {
    if (el.closest('[hidden], dialog:not([open]), template')) return true;
    // Lo de dentro de un <details> cerrado (salvo su <summary>) no se ve.
    const plegado = el.closest('details:not([open])');
    if (plegado && !el.closest('summary')) return true;
    // «Saltar al contenido» espera fuera de la pantalla hasta que recibe el foco.
    const saltar = el.closest('.saltar');
    if (saltar && document.activeElement !== saltar) return true;
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return true;
      if (cs.position === 'absolute' && cs.clip !== 'auto' && cs.clip !== '') return true;
      const r = e.getBoundingClientRect();
      if (r.width <= 1 && r.height <= 1 && cs.overflow === 'hidden') return true;
    }
    const r = el.getBoundingClientRect();
    return r.width === 0 && r.height === 0;
  };
  const nombre = (el) => {
    let p = el.tagName.toLowerCase();
    if (el.id) p += '#' + el.id;
    else if (el.classList.length) p += '.' + [...el.classList].slice(0, 2).join('.');
    const t = (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ');
    return p + (t ? ' «' + t.slice(0, 30) + '»' : '');
  };
  const fallos = [];
  const se = document.scrollingElement;
  if (se.scrollHeight > vh + 1 || se.scrollWidth > vw + 1)
    fallos.push(`la página se desplaza (${se.scrollWidth}×${se.scrollHeight} en ${vw}×${vh})`);
  const main = document.querySelector('main');
  if (main && main.scrollHeight > main.clientHeight + 1)
    fallos.push(`<main> se desplaza (${main.scrollHeight} en ${main.clientHeight})`);

  const vistos = [...document.querySelectorAll('body *')].filter((el) => !oculto(el));
  for (const el of vistos) {
    const b = el.getBoundingClientRect();
    if (b.right > vw + 1 || b.left < -1 || b.bottom > vh + 1 || b.top < -1)
      fallos.push('fuera de la pantalla: ' + nombre(el));
  }
  // Fuera de su caja: lo de dentro de una tarjeta, un botón o una píldora no sobresale.
  const CAJAS = '.barra, .tarjeta, .semana-dia, .chip, .centro__pendiente, .centro__tarjeta, ' +
    '.perfil-tarjeta, .perfil-categoria, .opcion-radio, .opcion-check, .loseta, .desc, ' +
    '.tiempo, button, .boton, .campo';
  for (const caja of vistos.filter((el) => el.matches(CAJAS))) {
    const c = caja.getBoundingClientRect();
    for (const el of caja.querySelectorAll('*')) {
      if (oculto(el)) continue;
      const b = el.getBoundingClientRect();
      const sale = b.right > c.right + 2 || b.bottom > c.bottom + 2 ||
        b.left < c.left - 2 || b.top < c.top - 2;
      if (sale)
        fallos.push('se sale de su caja: ' + nombre(el) + ' en ' + nombre(caja));
    }
  }
  // Los elementos de una lista paginada que se ven no se montan unos sobre otros.
  for (const lista of document.querySelectorAll('[data-paginar]')) {
    const sel = lista.dataset.items;
    const items = [...(sel ? lista.querySelectorAll(sel) : lista.children)]
      .filter((el) => !oculto(el));
    for (let i = 0; i < items.length; i++)
      for (let j = i + 1; j < items.length; j++) {
        const a = items[i].getBoundingClientRect(), b = items[j].getBoundingClientRect();
        const x = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const y = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (x > 2 && y > 2)
          fallos.push('se montan: ' + nombre(items[i]) + ' y ' + nombre(items[j]));
      }
  }
  // Objetivos de 48 px o más (los enlaces dentro de un párrafo están exentos, WCAG 2.5.8).
  const OBJETIVOS = 'a[href], button, summary, select, input:not([type=hidden]), textarea';
  // Dos objetivos no se solapan (uno taparía al otro: no se podría pulsar).
  const objetivos = vistos.filter((e) => e.matches(OBJETIVOS));
  for (let i = 0; i < objetivos.length; i++)
    for (let j = i + 1; j < objetivos.length; j++) {
      const a = objetivos[i], b = objetivos[j];
      const etiqueta = a.closest('label');
      if (a.contains(b) || b.contains(a) || (etiqueta && etiqueta === b.closest('label'))) continue;
      const r = a.getBoundingClientRect(), s = b.getBoundingClientRect();
      const x = Math.min(r.right, s.right) - Math.max(r.left, s.left);
      const y = Math.min(r.bottom, s.bottom) - Math.max(r.top, s.top);
      if (x > 2 && y > 2) fallos.push('se tapan: ' + nombre(a) + ' y ' + nombre(b));
    }
  for (const el of objetivos) {
    if (el.tagName === 'A' && el.closest('p') && !el.classList.contains('boton')) continue;
    const t = el.matches('[type=checkbox], [type=radio]') ? (el.closest('label') || el) : el;
    const b = t.getBoundingClientRect();
    if (b.width < 47.5 || b.height < 47.5)
      fallos.push(`objetivo de ${Math.round(b.width)}×${Math.round(b.height)} px: ` + nombre(t));
  }
  // Con el peor perfil, ningún texto se queda por debajo del 80 % de la letra del perfil.
  if (letra) {
    const raiz = getComputedStyle(document.documentElement);
    const base = parseFloat(raiz.getPropertyValue('--tamano-base')) * parseFloat(raiz.fontSize);
    for (const el of vistos) {
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      if (fs < base * 0.79)
        fallos.push(`letra de ${fs.toFixed(1)} px (perfil ${base} px): ` + nombre(el));
    }
  }
  return [...new Set(fallos)];
}"""


def problemas_de_encuadre(page, letra=False):
    """Lista de lo que está mal encuadrado en la pantalla que se ve (vacía si nada)."""
    page.wait_for_timeout(200)  # paginar.js reparte en el fotograma siguiente
    return page.evaluate(_ENCUADRE, {"letra": letra})


def revisar(page, letra=False):
    """axe sin fallos y pantalla encuadrada (ver el docstring del módulo)."""
    sin_errores_axe(page)
    problemas = problemas_de_encuadre(page, letra)
    assert not problemas, "\n".join(problemas)


# Qué lista paginada esconde el elemento y en qué sentido hay que ir para verlo. Primero la
# de fuera (las partes de la pantalla) y después las de dentro (una lista dentro de una parte).
_DONDE = """(selector) => {
  const el = document.querySelector(selector);
  if (!el) return null;
  const listas = [];
  for (let n = el.parentElement; n; n = n.parentElement) {
    if (n.hasAttribute('data-paginar')) listas.unshift(n);
  }
  for (const lista of listas) {
    const sel = lista.dataset.items;
    const items = [...(sel ? lista.querySelectorAll(sel) : lista.children)];
    const i = items.findIndex((it) => it.contains(el));
    if (i < 0 || !items[i].hidden) continue;
    const visible = items.findIndex((it) => !it.hidden);
    return { id: lista.id, paso: visible >= 0 && visible > i ? -1 : 1 };
  }
  return null;
}"""


def ir_a(page, selector, intentos=30):
    """Pasa de pantalla hasta que el elemento está a la vista."""
    for _ in range(intentos):
        # Al cambiar de pantalla, las listas de dentro se vuelven a repartir en el fotograma
        # siguiente: se espera a que se asiente antes de mirar.
        page.wait_for_timeout(150)
        if page.locator(selector).first.is_visible():
            return
        donde = page.evaluate(_DONDE, selector)
        assert donde, f"{selector} no está en ninguna lista paginada y no se ve"
        page.click(f"[data-paginador='{donde['id']}'] [data-pag='{donde['paso']}']")
    assert page.locator(selector).first.is_visible(), selector
