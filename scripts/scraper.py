import sys
import os
import re
import json
import time
import random
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from tqdm import tqdm

import shutil

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import init_db, get_connection, save_listing, mark_page_completed, get_completed_pages, get_stats

BASE_URL = "https://www.car.gr/classifieds/parts/?user=1004439"
FALLBACK_BASE_URL = "https://autoexpo.car.gr/parts/"

def find_node_binary() -> str:
    which_node = shutil.which("node")
    if which_node:
        return which_node
    # Check Windows venv and local appdata
    venv_node = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "Scripts", "node.exe")
    if os.path.exists(venv_node):
        return venv_node
    local_node = os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\nodejs\node.exe")
    if os.path.exists(local_node):
        return local_node
    # Check standard macOS/Linux paths
    for p in ["/opt/homebrew/bin/node", "/usr/local/bin/node", "/usr/bin/node"]:
        if os.path.exists(p):
            return p
    return "node"

NODE_BIN = find_node_binary()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

def extract_nuxt_data(html_text: str) -> Optional[Dict[str, Any]]:
    """Extract and deserialize window.__NUXT__ using Node.js."""
    m = re.search(r'(window\.__NUXT__\s*=.*?;)\s*</script>', html_text, re.DOTALL)
    if not m:
        return None

    js_code = f"let window = {{}};\n{m.group(1)}\nconsole.log(JSON.stringify(window.__NUXT__));\n"
    
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js_code)
        temp_js = f.name

    try:
        proc = subprocess.run([NODE_BIN, temp_js], capture_output=True, text=True, encoding="utf-8", timeout=10)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    finally:
        if os.path.exists(temp_js):
            try:
                os.remove(temp_js)
            except Exception:
                pass

    return None

import threading
_thread_local = threading.local()

def get_thread_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        _thread_local.session = requests.Session(impersonate="safari17_0")
    return _thread_local.session

def fetch_page(page_num: int, max_retries: int = 4) -> List[Dict[str, Any]]:
    """Fetch a single page of parts listings from Autoexpo Car.gr."""
    url = f"{BASE_URL}&pg={page_num}" if page_num > 1 else BASE_URL
    session = get_thread_session()
    
    for attempt in range(max_retries):
        try:
            time.sleep(random.uniform(0.3, 0.5))
            resp = session.get(url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                nuxt_data = extract_nuxt_data(resp.text)
                if nuxt_data:
                    state = nuxt_data.get("state", {})
                    classifieds = state.get("classifieds", {})
                    search = classifieds.get("search", {})
                    rows = search.get("rows", [])
                    if isinstance(rows, list) and len(rows) > 0:
                        return rows
            elif resp.status_code == 429:
                time.sleep(12.0 + random.uniform(1.0, 3.0))
            elif resp.status_code == 403:
                time.sleep(3.0 * (attempt + 1))
        except Exception:
            time.sleep(2.0)
    
    return []

def fetch_item_detail(listing_id: int, max_retries: int = 4) -> Optional[Dict[str, Any]]:
    """Fetch detailed metadata for a specific listing (OEM codes, car compatibility, tags)."""
    url = f"https://www.car.gr/parts/view/{listing_id}/"
    session = get_thread_session()
    detail_headers = dict(HEADERS)
    detail_headers["Referer"] = BASE_URL

    for attempt in range(max_retries):
        try:
            resp = session.get(url, headers=detail_headers, timeout=15)
            if resp.status_code == 200:
                nuxt_data = extract_nuxt_data(resp.text)
                if nuxt_data:
                    view = nuxt_data.get("state", {}).get("classifieds", {}).get("view", {})
                    cl = view.get("classified") or {}
                    if cl:
                        specs = cl.get("specifications", [])
                        part_numbers = ""
                        for_makemodels = []
                        categories_list = []
                        condition = ""

                        for sp in specs:
                            name = sp.get("name")
                            if name == "part_number":
                                part_numbers = sp.get("value", "")
                            elif name == "for_makemodels":
                                for_makemodels = sp.get("value", [])
                            elif name == "category":
                                val = sp.get("value", [])
                                if isinstance(val, list):
                                    for c in val:
                                        cat_info = c.get("category", {})
                                        categories_list.append({
                                            "id": cat_info.get("id"),
                                            "name": cat_info.get("humanNamePlural") or cat_info.get("humanName")
                                        })
                            elif name == "condition":
                                condition = sp.get("value", "")

                        tags = [t.get("value", "").strip() for t in cl.get("tags", []) if t.get("value")]
                        
                        compat_strs = []
                        for v in for_makemodels:
                            make = v.get("make") or ""
                            model = v.get("model") or ""
                            yf = v.get("yearFrom") or ""
                            yt = v.get("yearTo") or ""
                            years = f" ({yf}-{yt})" if yf or yt else ""
                            compat_strs.append(f"{make} {model}{years}".strip())

                        cl["part_number"] = part_numbers
                        cl["for_makemodels"] = for_makemodels
                        cl["makesModelsSummary"] = ", ".join(compat_strs)
                        cl["categoriesList"] = categories_list
                        cl["condition"] = condition
                        cl["keywords"] = ", ".join(tags)
                        cl["tags"] = tags
                        return cl
            elif resp.status_code in (403, 429):
                time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.0 * (attempt + 1))

    return None

def scrape_catalog(max_pages: Optional[int] = None, workers: int = 4):
    """Scrape catalog of listings across pages."""
    init_db()
    conn = get_connection()

    total_pages = 739 if max_pages is None else min(max_pages, 739)
    completed_pages = get_completed_pages(conn)
    pages_to_fetch = [p for p in range(1, total_pages + 1) if p not in completed_pages]

    print(f"\n📊 Σύνολο Σελίδων Καταλόγου: {total_pages} (~17.730 αγγελίες)")
    print(f"✅ Ήδη ολοκληρωμένες: {len(completed_pages)} σελίδες")
    print(f"⏳ Σελίδες προς συλλογή: {len(pages_to_fetch)} σελίδες\n")

    if not pages_to_fetch:
        print("🎉 Όλες οι 739 σελίδες και οι 17.730 αγγελίες έχουν ήδη συλλεχθεί πλήρως στη βάση!")
        conn.close()
        return

    if pages_to_fetch:
        pbar = tqdm(total=len(pages_to_fetch), desc="📥 Συλλογή Καταλόγου", unit="σελίδα")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_page = {executor.submit(fetch_page, p): p for p in pages_to_fetch}
            
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    rows = future.result()
                    if rows:
                        for row in rows:
                            save_listing(conn, row, is_deep=False)
                        conn.commit()
                        mark_page_completed(conn, page_num, len(rows))
                    else:
                        rows_retry = fetch_page(page_num, max_retries=3)
                        if rows_retry:
                            for row in rows_retry:
                                save_listing(conn, row, is_deep=False)
                            conn.commit()
                            mark_page_completed(conn, page_num, len(rows_retry))
                except Exception as e:
                    print(f"Σφάλμα στη σελίδα {page_num}: {e}")
                finally:
                    pbar.update(1)

        pbar.close()

    stats = get_stats(conn)
    conn.close()

    print("\n" + "="*60)
    print(f"✅ Η συλλογή του καταλόγου ολοκληρώθηκε επιτυχώς!")
    print(f"📊 Συνολικές αγγελίες στη βάση: {stats['total_listings']:,}")
    print(f"🖼️ Συνολικές high-res φωτογραφίες: {stats['total_images']:,}")
    print("="*60 + "\n")

def enrich_deep_details(limit: Optional[int] = None, workers: int = 10):
    """Enrich listings with exact OEM codes, vehicle compatibility trees, and keywords."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT id FROM listings WHERE is_deep_scraped = 0 ORDER BY id DESC"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    pending_ids = [r[0] for r in cursor.fetchall()]
    conn.close()

    if not pending_ids:
        print("🎉 Όλες οι αγγελίες διαθέτουν ήδη πλήρη αναλυτικά OEM στοιχεία & συμβατότητα!")
        return

    print(f"\n🔬 Εκκίνηση Αναλυτικής Εξαγωγής (OEM Κωδικοί, Συμβατότητα Οχημάτων & Keywords)")
    print(f"📦 Αγγελίες προς ανάλυση: {len(pending_ids):,}")
    print(f"⚡ Παράλληλα Threads: {workers}\n")

    pbar = tqdm(total=len(pending_ids), desc="🔍 Βαθιά Ανάλυση Αγγελιών", unit="αγγελία")
    
    batch_size = 20
    for i in range(0, len(pending_ids), batch_size):
        chunk = pending_ids[i:i + batch_size]
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_id = {executor.submit(fetch_item_detail, lid): lid for lid in chunk}
            
            db_conn = get_connection()
            for future in as_completed(future_to_id):
                lid = future_to_id[future]
                try:
                    item_detail = future.result()
                    if item_detail:
                        save_listing(db_conn, item_detail, is_deep=True)
                    else:
                        cur = db_conn.cursor()
                        cur.execute("UPDATE listings SET is_deep_scraped = 1 WHERE id = ?", (lid,))
                except Exception as e:
                    print(f"Σφάλμα στο ID {lid}: {e}")
                finally:
                    pbar.update(1)
            
            db_conn.commit()
            db_conn.close()

    pbar.close()
    
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()

    print("\n" + "="*60)
    print(f"✅ Η αναλυτική εξαγωγή ολοκληρώθηκε!")
    print(f"🚗 Συνολικές συσχετίσεις οχημάτων: {stats['total_compat']:,}")
    print(f"🏷️ Συνολικά Keywords / Tags: {stats['total_tags']:,}")
    print("="*60 + "\n")

if __name__ == "__main__":
    scrape_catalog(max_pages=5)
    enrich_deep_details(limit=10)
