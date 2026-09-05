#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NEXOR · Scraper de precios Temu Colombia (COP)
==============================================
Usa Playwright (navegador real) para buscar cada producto en Temu Colombia
y extraer nombre + precio en pesos colombianos de los resultados.

IMPORTANTE (léelo)
------------------
* Temu protege el sitio con capchas anti-bot. Si aparece la "verificación de
  seguridad", resuélvela A MANO en la ventana del navegador y el script
  sigue solo.
* Ejecútalo desde tu computador (IP residencial + navegador real = muchas más
  probabilidades de pasar la verificación inicial).
* Uso de referencia. Revisa los términos de servicio del sitio.

Instalación (una sola vez):
    pip install playwright
    playwright install chromium

Uso:
    python scraper_temu.py                        # los 10 productos, con ventana
    python scraper_temu.py --query "guantes nitrilo 100"   # una sola búsqueda
    python scraper_temu.py --headless             # sin ventana (suele chocar con capcha)
    python scraper_temu.py --out precios_temu     # prefijo de archivos de salida

Salidas:
    precios_temu_AAAAMMDD_HHMMSS.json  (datos completos)
    precios_temu_AAAAMMDD_HHMMSS.csv   (tabla listo para abrir en Excel)
    raw/                               (HTML crudo por búsqueda, por si hay que revisar)
"""

import argparse
import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# NOTA: playwright se importa dentro de run() para poder mostrar un mensaje
# claro de instalación si la librería no está disponible.

BASE = "https://www.temu.com/co"
SEARCH_URL = "https://www.temu.com/co/search_result.html?search_key={query}"

# producto del catálogo NEXOR -> búsqueda que se hace en Temu
SEARCHES = [
    ("guantes-nitrilo", "guantes de nitrilo desechables 100 unidades"),
    ("mascarillas-quirurgicas", "mascarillas quirurgicas desechables 50 unidades"),
    ("jeringas-desechables", "jeringas desechables 3ml 5ml 10ml 20ml paquete"),
    ("gasas-y-apositos", "gasas esteriles 10x10 paquete"),
    ("batas-quirurgicas", "batas quirurgicas desechables aislamiento 10 unidades"),
    ("gorros-quirurgicos", "gorros quirurgicos desechables 100"),
    ("cubrezapatos", "cubrezapatos desechables 100"),
    ("torundas-alcohol", "toallitas alcohol 70 por ciento desechables"),
    ("sabanas-desechables", "papel de camilla desechable rollo"),
    ("termometros-desechables", "termometros desechables de franja 100"),
]

PRICE_RE = re.compile(r"\$\s?(\d{1,3}(?:[.,]\d{3})+)")
CAPTCHA_TEXTS = [
    "verificación de seguridad", "verification", "slide to complete the puzzle",
    "llena cada recuadro", "para continuar", "complete the verification",
]


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_price(text):
    m = PRICE_RE.search(text or "")
    if not m:
        return None
    try:
        return int(m.group(1).replace(".", "").replace(",", ""))
    except ValueError:
        return None


def dismiss_popups(page):
    """Cierra ventanas de región/consentimiento que a veces aparecen al inicio."""
    labels = ["aceptar", "continuar", "entendido", "empezar a comprar",
              "maybe later", "no thanks", "decline"]
    for label in labels:
        try:
            btn = page.locator("button:has-text('" + label + "')").first
            if btn.is_visible(timeout=600):
                btn.click(timeout=1500)
                time.sleep(0.8)
        except Exception:
            pass


def is_captcha(page):
    try:
        body = page.locator("body").inner_text(timeout=1500).lower()
    except Exception:
        return False
    return any(k in body for k in CAPTCHA_TEXTS)


def wait_for_products(page, wait_seconds=25, captcha_max=90):
    """Espera a que carguen resultados; si hay capcha avisa y espera al usuario."""
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_captcha(page):
            print("\n[CAPTCHA] Apareció la verificación de seguridad.",
                  "\nResuélvela A MANO en la ventana del navegador. Esperando... (máx "
                  + str(captcha_max) + " s)\n")
            cap_deadline = time.time() + captcha_max
            while time.time() < cap_deadline:
                time.sleep(1.5)
                if not is_captcha(page):
                    print("[OK] Verificación superada, continúo.\n")
                    break
            time.sleep(2)
            continue
        # hay producto si existe algún enlace interno o el body tiene pinta de resultados
        try:
            if page.locator("a[href*='goods_id'], a[href*='/goods_']").count() > 3:
                return True
        except Exception:
            pass
        try:
            page.mouse.wheel(0, 1400)
        except Exception:
            pass
        time.sleep(1.3)
    return False


def extract_products(page, limit=40):
    """Recorre los enlaces a productos que cargó Temu y saca título + precio."""
    js = """
    () => {
      const items = [];
      const seen = new Set();
      const sel = 'a[href*="goods_id"], a[href*="/goods_"], [data-goods-id] a';
      document.querySelectorAll(sel).forEach(a => {
        const txt = (a.innerText || '').replace(/\\s+/g, ' ').trim();
        if (!txt || seen.has(a.href)) return;
        seen.add(a.href);
        const prices = txt.match(/\\$\\s?\\d{1,3}(?:[.,]\\d{3})+/g) || [];
        const title = a.getAttribute('title') || a.getAttribute('aria-label') || txt.slice(0, 140);
        items.push({ href: a.href, title: title.trim(), txt: txt.slice(0, 260), price_text: prices.join(' | ') });
      });
      return items.slice(0, LIMIT);
    }
    """.replace("LIMIT", str(limit))
    try:
        raw = page.evaluate(js)
    except Exception as exc:
        print("  [warn] no se pudo extraer del DOM:", exc)
        return []
    products, seen = [], set()
    for it in raw or []:
        price = parse_price(it.get("price_text") or it.get("txt"))
        key = (it.get("title"), price)
        if not it.get("title") or key in seen:
            continue
        seen.add(key)
        products.append({
            "title": it["title"][:140],
            "price": price,
            "price_text": it.get("price_text"),
            "url": it.get("href"),
        })
    return products


def save_outputs(results, prefix):
    fecha = now_stamp()
    json_path = prefix + ".json"
    csv_path = prefix + ".csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"generado": fecha, "resultados": results}, f,
                  ensure_ascii=False, indent=2)

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["producto", "query", "titulo", "precio_cop", "url", "generado"])
        for r in results:
            for it in r.get("items", []):
                w.writerow([r["producto"], r["query"], it["title"],
                            it["price"] or "", it["url"], fecha])

    print("\n[OK] Resultados guardados en:", json_path)
    print("[OK] Tabla CSV en:", csv_path)


def run(items, headless):
    from playwright.sync_api import sync_playwright as _sp
    with _sp() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="es-CO",
            timezone_id="America/Bogota",
            viewport={"width": 1280, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"),
        )
        page = context.new_page()
        print("[NAV] Abriendo Temu Colombia…")
        try:
            page.goto(BASE, timeout=60000, wait_until="domcontentloaded")
        except Exception as exc:
            print("  [warn] goto home:", exc)
        time.sleep(3)
        dismiss_popups(page)

        results = []
        for key, query in items:
            url = SEARCH_URL.format(query=query.replace(" ", "+"))
            print("\n[BUSCA] " + key + " → «" + query + "»")
            try:
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception as exc:
                print("  [warn] goto:", exc)
            ok = wait_for_products(page)
            raw_dir = Path("raw")
            raw_dir.mkdir(exist_ok=True)
            (raw_dir / (re.sub(r"[^a-z0-9]+", "-", key) + ".html")).write_text(
                page.content(), encoding="utf-8")
            items_found = extract_products(page) if ok else []
            print("  -> " + str(len(items_found)) + " ítem(s) extraídos")
            for pr in items_found[:8]:
                cu = ("$" + format(pr["price"], ",d")) if pr["price"] else (pr["price_text"] or "s/precio")
                print("     • " + (pr["title"][:58]) + "  |  " + cu)
            results.append({"producto": key, "query": query, "url": url,
                            "items": items_found})
        browser.close()
        return results


def main():
    ap = argparse.ArgumentParser(
        description="Scraper de precios de suministros médicos en Temu Colombia (COP).")
    ap.add_argument("--headless", action="store_true",
                    help="sin ventana (es más probable que salte el capcha)")
    ap.add_argument("--query", help="una sola búsqueda libre")
    ap.add_argument("--out", default=None,
                    help="prefijo de archivos de salida "
                         "(por defecto: precios_temu_AAAAMMDD_HHMMSS)")
    ap.add_argument("--max", type=int, default=40, help="ítems máximos por búsqueda")
    args = ap.parse_args()

    items = SEARCHES
    if args.query:
        items = [("busqueda-libre", args.query)]

    try:
        results = run(items, args.headless)
    except Exception as exc:
        print("\n[ERROR] " + str(exc))
        print("¿Instalaste las dependencias?  →  pip install -r requirements.txt")
        print("¿Descargaste el navegador?      →  playwright install chromium")
        sys.exit(1)

    prefix = args.out or ("precios_temu_" + now_stamp())
    save_outputs(results, prefix)

    print("\nSiguiente paso: copia los precios que veas a tu gusto en "
          "la tabla y me los pasas; actualizo index.html al instante.")


if __name__ == "__main__":
    main()