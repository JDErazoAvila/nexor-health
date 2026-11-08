# -*- coding: utf-8 -*-
"""Extractor de listados públicos de GMD Colombia. Exporta CSV UTF-8 con BOM."""
import csv, logging, re, sys, time
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE = 'https://www.gmd.com.co/'
SEED = 'https://www.gmd.com.co/category/todos-los-productos/0ZGVT000000004r4AA?page=1&category=0ZGVT000000004r4AA'
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = PROJECT_ROOT / 'Datos' / 'Catálogos' / 'productos-gmd-catalogo-completo.csv'
LOG = PROJECT_ROOT / 'Logs' / 'Catálogo-GMD' / 'errores.log'
OUT.parent.mkdir(parents=True, exist_ok=True)
LOG.parent.mkdir(parents=True, exist_ok=True)
PAUSE = 1.2
TIMEOUT = 45000
MAX_PAGES = 500
HEADLESS = True
logging.basicConfig(filename=LOG, level=logging.INFO, encoding='utf-8', format='%(asctime)s | %(levelname)s | %(message)s')
console = logging.StreamHandler(sys.stdout); console.setLevel(logging.INFO); console.setFormatter(logging.Formatter('%(levelname)s: %(message)s')); logging.getLogger().addHandler(console)

def clean(s): return re.sub(r'\s+', ' ', str(s or '')).strip()
def internal_url(href, base):
    if not href: return ''
    u = urljoin(base, href.strip())
    if urlparse(u).netloc.lower() not in ('www.gmd.com.co', 'gmd.com.co'): return ''
    p = urlparse(u)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ''))
def cat_id(url):
    q = parse_qs(urlparse(url).query)
    return q.get('category', [urlparse(url).path.rstrip('/').split('/')[-1]])[0]
def make_page_url(url, n):
    p = urlparse(url); q = parse_qs(p.query, keep_blank_values=True)
    q['page'] = [str(n)]
    q.setdefault('category', [cat_id(url)])
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q, doseq=True), ''))

def get_categories(page, base):
    raw = page.locator('a[href*="/category/"]').evaluate_all('(els) => els.map(a => a.href)')
    out=[]
    for href in raw:
        u=internal_url(href, base)
        if not u: continue
        path=urlparse(u).path.lower()
        if '/category/' not in path or '/category/detail/' in path: continue
        if u not in out: out.append(u)
    return out

def get_cards(page):
    # Busca enlaces de ficha de producto y sube al contenedor visual más cercano.
    return page.evaluate(r'''() => {
      const visible=e=>{if(!e)return false;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'};
      const links=[...document.querySelectorAll('a[href]')].filter(a=>visible(a)&&(/\/product\//i.test(a.getAttribute('href')||'')||/\/s\/product\//i.test(a.getAttribute('href')||'')||/\/products?\//i.test(a.getAttribute('href')||'')));
      const seen=new Set(),out=[];
      for(const a of links){const href=(a.href||'').split('#')[0];if(!href||seen.has(href))continue;seen.add(href);
        let node=a;for(let i=0;i<7&&node.parentElement;i++){const t=(node.innerText||'').trim(),n=node.querySelectorAll('a[href]').length;if(t.length>8&&t.length<2500&&n<=8&&(node.querySelector('img')||/precio|\$|SKU|referencia|agotado|disponible/i.test(t)))break;node=node.parentElement;}
        const text=(node.innerText||a.innerText||'').trim(),img=node.querySelector('img'),titleLink=[...node.querySelectorAll('a[href]')].find(x=>/\/product\//i.test(x.getAttribute('href')||'')||/\/s\/product\//i.test(x.getAttribute('href')||'')||/\/products?\//i.test(x.getAttribute('href')||''))||a;
        const title=(titleLink.innerText||titleLink.title||(img&&img.alt)||'').trim(),lines=text.split(/\n+/).map(x=>x.trim()).filter(Boolean);
        const sku=text.match(/(?:SKU|referencia|c[oó]digo|REF\.?)\s*[:#\-]?\s*([A-Z0-9][A-Z0-9._\/-]{2,})/i),code=lines.find(x=>/^[A-Z0-9][A-Z0-9._/-]{2,30}$/.test(x)&&/[A-Z]/i.test(x)&&/\d/.test(x));
        const price=text.match(/(?:COP\s*)?\$\s*[\d.,]+(?:\s*(?:COP|IVA incluido))?/i),status=lines.find(x=>/disponible|agotado|sin existencias|no disponible|en inventario/i.test(x))||'';
        out.push({url:href,nombre:title||(img&&img.alt)||'',texto:text,referencia:sku?sku[1]:(code||''),precio:price?price[0].trim():'',disponibilidad:status,imagen:img?(img.currentSrc||img.src||img.getAttribute('data-src')||''):''});
      }return out;
    }''')

def wait_page(page):
    try: page.wait_for_load_state('networkidle', timeout=9000)
    except PlaywrightTimeoutError: pass
    page.wait_for_timeout(700)

def crawl_category(browser, category_url, products, seen_products):
    name=''; previous=None; done=0
    for number in range(1, MAX_PAGES+1):
        url=make_page_url(category_url, number); page=browser.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=TIMEOUT); wait_page(page)
            if not name:
                try: name=clean(page.locator('h1').first.inner_text(timeout=1500))
                except Exception: name=clean(page.title())
            cards=get_cards(page)
            if not cards and number==1 and url!=category_url:
                page.goto(category_url, wait_until='domcontentloaded', timeout=TIMEOUT); wait_page(page); cards=get_cards(page)
            if not cards:
                if number==1: logging.info('No se detectaron tarjetas en %s (%s)', name, url)
                break
            signature=tuple(sorted(x.get('url','') for x in cards if x.get('url')))
            if signature and signature==previous:
                logging.info('La página %s repite los resultados; fin de categoría %s', number, name); break
            previous=signature
            new=0
            for c in cards:
                product_url=clean(c.get('url'))
                if not product_url or product_url in seen_products: continue
                seen_products.add(product_url); txt=clean(c.get('texto'))
                bm=re.search(r'(?:Marca|Fabricante)\s*:\s*([^\n|,;]{2,60})', txt, re.I)
                price=clean(c.get('precio'))
                products.append({'referencia':clean(c.get('referencia')),'nombre_producto':clean(c.get('nombre')),'marca':clean(bm.group(1)) if bm else '', 'precio_publicado':price,'moneda':'COP' if re.search(r'\bCOP\b|\$',price,re.I) else '', 'disponibilidad':clean(c.get('disponibilidad')),'url_producto':product_url,'imagen':clean(c.get('imagen')),'categoria':name,'url_categoria':category_url,'pagina':number,'texto_visible_tarjeta':txt})
                new+=1
            done+=1; logging.info('Categoría %s | página %s | tarjetas %s | nuevos %s | únicos %s',name or category_url,number,len(cards),new,len(products))
            page.close(); time.sleep(PAUSE)
        except PlaywrightTimeoutError as e:
            logging.error('Tiempo agotado en %s: %s',url,e); page.close()
            if number==1: break
            time.sleep(PAUSE)
        except Exception as e:
            logging.exception('Error procesando %s: %s',url,e); page.close()
            if number==1: break
            time.sleep(PAUSE)
    return done

def main():
    products=[]; seen_products=set(); seen_categories=set(); queue=deque([SEED])
    logging.info('Inicio del extractor GMD')
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=HEADLESS)
        home=browser.new_page()
        try:
            home.goto(BASE,wait_until='domcontentloaded',timeout=TIMEOUT); wait_page(home)
            for u in get_categories(home,BASE): queue.append(u)
        except Exception as e: logging.exception('No se pudieron descubrir categorías desde inicio: %s',e)
        finally: home.close()
        while queue:
            u=internal_url(queue.popleft(),BASE)
            if not u or u in seen_categories: continue
            seen_categories.add(u); logging.info('Explorando categoría: %s',u)
            discovery=browser.new_page()
            try:
                discovery.goto(u,wait_until='domcontentloaded',timeout=TIMEOUT); wait_page(discovery)
                for child in get_categories(discovery,u):
                    if child not in seen_categories: queue.append(child)
            except Exception as e: logging.warning('No se pudieron descubrir subcategorías en %s: %s',u,e)
            finally: discovery.close()
            crawl_category(browser,u,products,seen_products)
        browser.close()
    unique={}
    for row in products:
        key=row['url_producto'] or row['referencia'] or row['nombre_producto']
        if not key: continue
        if key not in unique: unique[key]=row
        else:
            for k,v in row.items():
                if not unique[key].get(k) and v: unique[key][k]=v
    columns=['referencia','nombre_producto','marca','precio_publicado','moneda','disponibilidad','url_producto','imagen','categoria','url_categoria','pagina','texto_visible_tarjeta']
    with open(OUT,'w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=columns,delimiter=';',extrasaction='ignore'); w.writeheader(); w.writerows(unique.values())
    logging.info('Finalizado | categorías visitadas: %s | productos únicos: %s',len(seen_categories),len(unique))
    print('\nProceso terminado.')
    print(f'Categorías visitadas: {len(seen_categories)}')
    print(f'Productos únicos exportados: {len(unique)}')
    print(f'CSV: {OUT}')
    print(f'Log: {LOG}')
    if not unique: print('ATENCIÓN: no se detectaron productos; revise errores_gmd.log y ajuste los selectores si cambió el diseño del sitio.')

if __name__=='__main__': main()
