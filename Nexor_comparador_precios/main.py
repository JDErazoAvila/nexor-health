#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NEXOR - Comparador público de precios por SKU.

- Consulta únicamente páginas públicas y permitidas por robots.txt.
- No inicia sesión ni intenta eludir bloqueos.
- Detiene las consultas a un dominio al recibir HTTP 401/403/429.
- Guarda resultados y estados por sitio durante la ejecución.
- Permite reanudar con: python main.py --reanudar
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
SKU_FILE = ROOT / "sku_gmd.txt"
SITES_FILE = ROOT / "competidores.txt"
REPORT_DIR = ROOT / "Reports"
LOG_DIR = ROOT / "Logs"
CHECKPOINT_DIR = ROOT / "Checkpoints"

SITES_DEFAULT = [
    "https://tiendamedicalospinos.com", "https://tmvco.com.co",
    "https://saluti.com.co", "https://ortopedicosfuturo.com",
    "https://gmd.com.co", "https://allers.com.co",
    "https://tecnomedica.com.co", "https://medicolsa.com.co",
    "https://novamedicasas.com", "https://imecolombia.com",
    "https://coimpormedica.com", "https://distrimedics.com",
    "https://promedco.com", "https://cimexcolombiasas.com",
    "https://tiendamedica.com.co", "https://tiendasmedicascolombia.com",
    "https://caldasmedicas.com", "https://corazonmedico.com.co",
    "https://dismecol.com", "https://tmmedicas.com",
    "https://labotekcolombia.com", "https://sidsalud.com",
    "https://medicox.com.co", "https://intercomercialmedica.com",
    "https://ortopedicos.com.co", "https://morthopedics.com",
    "https://biomaxcolombia.com", "https://quirurgicosgl.com",
    "https://medical-colombia.com", "https://bbraun.com",
    "https://hospitalaria.com.co", "https://sumimedical.com",
    "https://disortho.com.co", "https://furesa.co",
    "https://almar-medica.com",
]

# Sustituye el correo de contacto por uno real si mantendrás este robot.
USER_AGENT = "NEXORPriceResearchBot/1.1 (public product price research)"
TIMEOUT = 18
REQUEST_DELAY_SECONDS = 2.0
MAX_SITEMAP_URLS_PER_SITE = 5000
MAX_FALLBACK_LINKS = 150
MIN_PRICE = 1
MAX_PRICE = 2_000_000_000

RESULT_COLUMNS = [
    "SKU", "Competidor", "Sitio", "Producto encontrado", "Marca",
    "Precio publicado COP", "Moneda detectada", "Disponibilidad publicada",
    "Unidad detectada", "Tipo de coincidencia", "Evidencia SKU",
    "Evidencia precio", "URL producto", "Fecha consulta", "Estado",
]


def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("nexor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # Evita duplicar handlers si se vuelve a invocar desde otro entorno.
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh = logging.FileHandler(LOG_DIR / "ejecucion.log", encoding="utf-8")
        sh = logging.StreamHandler()
        fh.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger

log = setup_logging()


def normalize_sku(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip().strip('"').strip("'") for line in
            path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def load_skus() -> list[str]:
    values = read_lines(SKU_FILE)
    seen, output = set(), []
    for value in values:
        key = normalize_sku(value)
        if key and key not in seen and key not in {"ND", "NODISPONIBLE"}:
            seen.add(key)
            output.append(value.strip())
    if not output:
        raise SystemExit("No hay SKU válidos en sku_gmd.txt (uno por línea).")
    return output


def load_sites() -> list[str]:
    values = read_lines(SITES_FILE) or SITES_DEFAULT
    sites = []
    for value in values:
        if not value.startswith(("http://", "https://")):
            value = "https://" + value
        sites.append(value.rstrip("/"))
    return list(dict.fromkeys(sites))


def parse_price(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        s = re.sub(r"[^\d,.\-]", "", str(value).strip())
        if not s:
            return None
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
        elif "," in s:
            tail = s.split(",")[-1]
            s = s.replace(",", ".") if len(tail) in (1, 2) else s.replace(",", "")
        elif s.count(".") > 1 or ("." in s and len(s.split(".")[-1]) == 3):
            s = s.replace(".", "")
        try:
            number = float(s)
        except ValueError:
            return None
    return round(number, 2) if MIN_PRICE <= number <= MAX_PRICE else None


class SiteClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.domain = urlparse(self.base).netloc.lower()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-CO,es;q=0.9,en;q=0.7",
        })
        self.robot = RobotFileParser()
        self.robot_ok = False
        self.blocked = False
        self.limited = False
        self.limit_code = None
        self.last_request = 0.0
        robots_url = urljoin(self.base + "/", "robots.txt")
        try:
            r = self.session.get(robots_url, timeout=TIMEOUT)
            if r.status_code == 200:
                self.robot.parse(r.text.splitlines())
                self.robot_ok = True
            elif r.status_code in (401, 403):
                self.blocked = True
                log.warning("%s: robots.txt restringido (HTTP %s); se omite.", self.domain, r.status_code)
        except requests.RequestException as exc:
            # Sin robots.txt accesible se conserva una política conservadora de baja frecuencia.
            log.warning("%s: no fue posible leer robots.txt (%s).", self.domain, exc)

    def allowed(self, url: str) -> bool:
        if self.blocked or self.limited:
            return False
        if self.robot_ok:
            try:
                return self.robot.can_fetch(USER_AGENT, url)
            except Exception:
                return False
        return True

    def get(self, url: str):
        if not self.allowed(url):
            return None
        wait = REQUEST_DELAY_SECONDS - (time.monotonic() - self.last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            response = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
            self.last_request = time.monotonic()
            if response.status_code in (401, 403, 429):
                self.limited = True
                self.limit_code = response.status_code
                log.warning("%s: HTTP %s; se detienen TODAS las consultas a este dominio.", self.domain, response.status_code)
                return None
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            self.last_request = time.monotonic()
            log.warning("%s: error consultando %s: %s", self.domain, url, exc)
            return None

    def sitemap_urls(self) -> list[str]:
        candidates = [urljoin(self.base + "/", p) for p in
                      ("sitemap.xml", "sitemap_index.xml", "sitemap_index.xml.gz")]
        found, visited = [], set()

        def parse_map(map_url: str, depth: int = 0):
            if (self.limited or self.blocked or map_url in visited or depth > 2
                    or len(found) >= MAX_SITEMAP_URLS_PER_SITE):
                return
            visited.add(map_url)
            response = self.get(map_url)
            if response is None:
                return
            try:
                root = ET.fromstring(response.content)
            except ET.ParseError:
                return
            locs = [el.text.strip() for el in root.iter()
                    if el.tag.lower().endswith("loc") and el.text]
            if root.tag.lower().endswith("sitemapindex"):
                for loc in locs[:60]:
                    if urlparse(loc).netloc.lower() == self.domain:
                        parse_map(loc, depth + 1)
                    if self.limited:
                        break
            else:
                for loc in locs:
                    p = urlparse(loc)
                    if p.netloc.lower() == self.domain and p.scheme in ("http", "https"):
                        found.append(urldefrag(loc)[0])
                    if len(found) >= MAX_SITEMAP_URLS_PER_SITE:
                        break

        for candidate in candidates:
            parse_map(candidate)
            if found or self.limited or self.blocked:
                break
        return list(dict.fromkeys(found))[:MAX_SITEMAP_URLS_PER_SITE]

    def fallback_links(self) -> list[str]:
        if self.limited or self.blocked:
            return []
        response = self.get(self.base + "/")
        if response is None:
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        links = []
        for a in soup.select("a[href]"):
            url = urldefrag(urljoin(self.base + "/", a.get("href", "")))[0]
            p = urlparse(url)
            if p.scheme in ("http", "https") and p.netloc.lower() == self.domain:
                if any(w in url.lower() for w in ("product", "producto", "shop", "tienda", "catalog", "catalogo", "item")):
                    links.append(url)
        return list(dict.fromkeys(links))[:MAX_FALLBACK_LINKS]


def flatten_jsonld(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from flatten_jsonld(item)
    elif isinstance(obj, dict):
        yield obj
        if obj.get("@graph"):
            yield from flatten_jsonld(obj["@graph"])


def extract_product_data(soup: BeautifulSoup) -> dict:
    data = {"producto": "", "marca": "", "precio": None, "moneda": "",
            "disponibilidad": "SIN_INFORMACION", "unidad": "", "evidencia": ""}
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            raw = json.loads(tag.string or tag.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in flatten_jsonld(raw):
            types = obj.get("@type", [])
            if isinstance(types, str):
                types = [types]
            if not any(isinstance(t, str) and t.endswith("Product") for t in types):
                continue
            data["producto"] = obj.get("name") or data["producto"]
            brand = obj.get("brand")
            if isinstance(brand, dict):
                brand = brand.get("name")
            data["marca"] = brand or data["marca"]
            offers = obj.get("offers", {})
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                price = parse_price(offers.get("price") or offers.get("lowPrice"))
                if price is not None:
                    data["precio"] = price
                    data["moneda"] = offers.get("priceCurrency", "")
                    data["evidencia"] = "JSON-LD Offer"
                av = str(offers.get("availability", "")).lower()
                if "instock" in av:
                    data["disponibilidad"] = "DISPONIBLE_PUBLICAMENTE"
                elif "outofstock" in av or "soldout" in av:
                    data["disponibilidad"] = "AGOTADO_PUBLICAMENTE"
    def meta(*selectors):
        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return el.get("content") or el.get("value") or el.get_text(" ", strip=True)
        return ""
    data["producto"] = data["producto"] or meta('meta[property="og:title"]', 'meta[name="twitter:title"]') or (soup.title.get_text(" ", strip=True) if soup.title else "")
    data["marca"] = data["marca"] or meta('meta[itemprop="brand"]')
    if data["precio"] is None:
        raw_price = meta('meta[property="product:price:amount"]', 'meta[property="og:price:amount"]', 'meta[itemprop="price"]', 'meta[name="price"]')
        price = parse_price(raw_price)
        if price is not None:
            data["precio"] = price
            data["moneda"] = meta('meta[property="product:price:currency"]', 'meta[property="og:price:currency"]')
            data["evidencia"] = "Meta precio"
    text = soup.get_text(" ", strip=True).lower()
    if data["disponibilidad"] == "SIN_INFORMACION":
        if any(x in text for x in ("agotado", "sin existencias", "no disponible", "out of stock")):
            data["disponibilidad"] = "AGOTADO_PUBLICAMENTE"
        elif any(x in text for x in ("añadir al carrito", "agregar al carrito", "comprar", "add to cart")):
            data["disponibilidad"] = "PUBLICADO_COMO_COMPRABLE"
    unit = re.search(r"\b(caja|paquete|unidad|par|kit|set|frasco|rollo)\b", text, re.I)
    if unit:
        data["unidad"] = unit.group(1).lower()
    return data


def page_contains_sku(soup: BeautifulSoup, sku: str) -> tuple[bool, str]:
    target = normalize_sku(sku)
    selectors = ('[itemprop="sku"]', '[itemprop="mpn"]', '[data-sku]', '[class*="sku"]', '[id*="sku"]', 'meta[name="sku"]')
    for selector in selectors:
        for el in soup.select(selector):
            vals = [el.get("content", ""), el.get("data-sku", ""), el.get_text(" ", strip=True)]
            if any(normalize_sku(v) == target for v in vals if v):
                return True, "SKU exacto en campo"
    # Token independiente; no normalizar el texto completo porque uniría palabras distintas.
    text = soup.get_text(" ", strip=True).upper()
    if re.search(r"(?<![A-Z0-9])" + re.escape(sku.upper()) + r"(?![A-Z0-9])", text):
        return True, "SKU exacto en texto"
    return False, ""


def save_checkpoint(site_key: str, rows: list[dict], stats: dict):
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", site_key)
    # Escritura atómica para no dejar archivos JSON truncados.
    tmp = CHECKPOINT_DIR / f"{safe}.json.tmp"
    target = CHECKPOINT_DIR / f"{safe}.json"
    tmp.write_text(json.dumps({"results": rows, "stats": stats}, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)


def scan_site(site: str, skus: list[str]) -> tuple[list[dict], dict]:
    client = SiteClient(site)
    domain = urlparse(site).netloc
    stats = {"sitio": site, "paginas_encontradas": 0, "paginas_revisadas": 0,
             "coincidencias": 0, "estado": "OK", "detalle": ""}
    if client.blocked:
        stats.update(estado="RESTRINGIDO", detalle="robots.txt restringido")
        return [], stats
    urls = client.sitemap_urls()
    if not urls and not client.limited:
        urls = client.fallback_links()
        stats["detalle"] = "Sin sitemap utilizable; se revisaron enlaces públicos limitados"
    stats["paginas_encontradas"] = len(urls)
    if client.limited:
        stats.update(estado="LIMITADO_POR_SERVIDOR", detalle=f"HTTP {client.limit_code}; se detuvo el dominio")
        return [], stats
    if not urls:
        stats.update(estado="SIN_CATALOGO_DETECTABLE", detalle=stats["detalle"] or "No se detectaron URLs públicas de producto")
        return [], stats

    results = []
    for index, url in enumerate(urls, 1):
        if client.limited:
            break
        response = client.get(url)
        if client.limited:
            break
        if response is None or "html" not in response.headers.get("Content-Type", "").lower():
            continue
        stats["paginas_revisadas"] += 1
        soup = BeautifulSoup(response.text, "html.parser")
        for sku in skus:
            found, evidence = page_contains_sku(soup, sku)
            if not found:
                continue
            info = extract_product_data(soup)
            currency = (info["moneda"] or "").upper()
            price_cop = info["precio"] if currency in ("", "COP") else None
            results.append({
                "SKU": sku, "Competidor": domain, "Sitio": site,
                "Producto encontrado": info["producto"], "Marca": info["marca"],
                "Precio publicado COP": price_cop,
                "Moneda detectada": currency or "NO_INDICADA",
                "Disponibilidad publicada": info["disponibilidad"],
                "Unidad detectada": info["unidad"], "Tipo de coincidencia": "EXACTA",
                "Evidencia SKU": evidence, "Evidencia precio": info["evidencia"],
                "URL producto": response.url,
                "Fecha consulta": datetime.now().isoformat(timespec="seconds"),
                "Estado": "PRECIO_ENCONTRADO" if price_cop is not None else "SKU_SIN_PRECIO",
            })
            stats["coincidencias"] += 1
        if index % 50 == 0:
            log.info("%s: %s/%s páginas; %s coincidencias", domain, index, len(urls), stats["coincidencias"])
    if client.limited:
        stats.update(estado="LIMITADO_POR_SERVIDOR", detalle=f"HTTP {client.limit_code}; se detuvo el dominio")
    elif stats["coincidencias"] == 0:
        stats["estado"] = "SIN_COINCIDENCIAS"
    return results, stats


def write_reports(skus: list[str], sites: list[str], all_results: list[dict], site_stats: list[dict], run_id: str):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(all_results, columns=RESULT_COLUMNS)
    found = set(results_df["SKU"].dropna().tolist())
    missing = pd.DataFrame([{"SKU": s, "Estado": "SIN_COINCIDENCIA_EN_FUENTES_CONSULTADAS"} for s in skus if s not in found])
    priced = results_df[results_df["Precio publicado COP"].notna()].copy()
    if not priced.empty:
        summary = priced.groupby("SKU")["Precio publicado COP"].agg(Competidores_con_precio="count", Precio_minimo="min", Precio_promedio="mean", Precio_maximo="max").reset_index()
        best = priced.sort_values("Precio publicado COP").groupby("SKU", as_index=False).first()
        best = best[["SKU", "Competidor", "Producto encontrado", "Precio publicado COP", "URL producto"]].merge(summary, on="SKU", how="left")
    else:
        best = pd.DataFrame(columns=["SKU", "Competidor", "Producto encontrado", "Precio publicado COP", "URL producto", "Competidores_con_precio", "Precio_minimo", "Precio_promedio", "Precio_maximo"])
    stats_df = pd.DataFrame(site_stats)
    xlsx = REPORT_DIR / f"comparacion_precios_{run_id}.xlsx"
    csv = REPORT_DIR / f"resultados_detallados_{run_id}.csv"
    results_df.to_csv(csv, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        pd.DataFrame({"Indicador": ["SKU únicos consultados", "Sitios configurados", "Coincidencias SKU", "Coincidencias con precio", "SKU sin coincidencia"],
                      "Resultado": [len(skus), len(sites), len(results_df), len(priced), len(missing)]}).to_excel(writer, sheet_name="Resumen", index=False)
        results_df.to_excel(writer, sheet_name="Comparacion", index=False)
        best.to_excel(writer, sheet_name="Mejor precio", index=False)
        missing.to_excel(writer, sheet_name="Sin coincidencias", index=False)
        stats_df.to_excel(writer, sheet_name="Estado sitios", index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max((len(str(c.value or "")) for c in col[:200]), default=10)
                ws.column_dimensions[letter].width = min(max(max_len + 2, 12), 48)
    return xlsx, csv


def main():
    parser = argparse.ArgumentParser(description="Comparador público NEXOR")
    parser.add_argument("--reanudar", action="store_true", help="Carga sitios terminados del último conjunto de checkpoints")
    args = parser.parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    skus, sites = load_skus(), load_sites()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log.info("Inicio: %s SKU únicos; %s sitios. Modo: %s", len(skus), len(sites), "reanudar" if args.reanudar else "nuevo")

    all_results, site_stats = [], []
    completed = set()
    if args.reanudar:
        for site in sites:
            key = re.sub(r"[^a-zA-Z0-9_-]", "_", urlparse(site).netloc.lower())
            cp = CHECKPOINT_DIR / f"{key}.json"
            if cp.exists():
                try:
                    payload = json.loads(cp.read_text(encoding="utf-8"))
                    all_results.extend(payload.get("results", []))
                    site_stats.append(payload.get("stats", {}))
                    completed.add(site)
                except (json.JSONDecodeError, OSError) as exc:
                    log.warning("Checkpoint inválido para %s: %s; se volverá a consultar.", site, exc)
    pending = [s for s in sites if s not in completed]
    log.info("Sitios ya guardados: %s; pendientes: %s", len(completed), len(pending))

    # Secuencial deliberadamente: reduce carga y hace más sencillo respetar bloqueos.
    for index, site in enumerate(pending, 1):
        log.info("[%s/%s] Consultando %s", index, len(pending), site)
        try:
            rows, stats = scan_site(site, skus)
        except Exception as exc:
            log.exception("Error no controlado en %s: %s", site, exc)
            rows = []
            stats = {"sitio": site, "paginas_encontradas": 0, "paginas_revisadas": 0,
                     "coincidencias": 0, "estado": "ERROR", "detalle": str(exc)}
        all_results.extend(rows)
        site_stats.append(stats)
        key = re.sub(r"[^a-zA-Z0-9_-]", "_", urlparse(site).netloc.lower())
        save_checkpoint(key, rows, stats)
        # Publica un avance recuperable después de cada sitio.
        try:
            xlsx, csv = write_reports(skus, sites, all_results, site_stats, run_id)
            log.info("Avance guardado: %s filas; %s", len(all_results), xlsx.name)
        except Exception as exc:
            log.exception("No se pudo actualizar el informe parcial: %s", exc)
        log.info("Sitio finalizado: %s | %s | %s coincidencias", site, stats["estado"], stats["coincidencias"])

    xlsx, csv = write_reports(skus, sites, all_results, site_stats, run_id)
    log.info("Proceso terminado. Excel: %s | CSV: %s", xlsx, csv)
    log.info("Nota: no encontrar un SKU en las páginas consultadas no demuestra que el producto no exista.")

if __name__ == "__main__":
    main()
