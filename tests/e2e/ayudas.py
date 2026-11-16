"""Ayudas comunes de las pruebas en navegador.

Sin desplazamiento (decisión 0005): lo que no cabe está en otra pantalla de la misma página
y se llega con «Anterior / Siguiente», como haría una persona.
"""

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
