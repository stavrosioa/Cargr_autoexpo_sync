import os
import sys
import csv
import time
import json
import sqlite3
from typing import List, Dict, Set, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import init_db, get_connection, save_listing, mark_page_completed, DB_PATH, DB_DIR
from scraper import fetch_page, extract_nuxt_data, BASE_URL, HEADERS

def scan_live_catalog_ids(workers: int = 2) -> Dict[int, Dict[str, Any]]:
    """Scan all live pages and collect listing IDs + titles + prices."""
    print("🌐 Σάρωση ενεργού καταλόγου Car.gr για συλλογή όλων των live IDs...")
    
    total_pages = 739
    pbar = tqdm(total=total_pages, desc="🔍 Έλεγχος Live Αγγελιών", unit="σελίδα")
    
    live_items: Dict[int, Dict[str, Any]] = {}
    
    def process_page(p: int) -> List[Dict[str, Any]]:
        return fetch_page(p)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_page = {executor.submit(process_page, p): p for p in range(1, total_pages + 1)}
        for future in as_completed(future_to_page):
            p = future_to_page[future]
            try:
                rows = future.result()
                if rows:
                    for r in rows:
                        lid = r.get("id")
                        if lid:
                            live_items[lid] = {
                                "id": lid,
                                "title": r.get("title") or r.get("descriptiveTitle") or "",
                                "price": r.get("price", {}).get("value") if isinstance(r.get("price"), dict) else str(r.get("price") or ""),
                                "url": f"https://www.car.gr/parts/view/{lid}/",
                                "raw": r,
                                "page": p
                            }
            except Exception:
                pass
            finally:
                pbar.update(1)
                
    pbar.close()
    return live_items

def get_db_listings() -> Dict[int, Dict[str, Any]]:
    """Retrieve all listings currently stored in the SQLite database."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, title, price, is_active, is_deep_scraped, photo_count, scraped_at 
    FROM listings
    """)
    rows = cursor.fetchall()
    conn.close()
    
    db_items: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        db_items[r["id"]] = dict(r)
    return db_items

def run_sync_audit(
    fetch_missing: bool = False,
    mark_inactive: bool = False,
    export_csv: bool = True,
    workers: int = 2
):
    """Compare Live Car.gr vs Local DB and perform automated synchronization."""
    print("\n" + "=" * 75)
    print("🔄 ΡΟΥΤΙΝΑ ΣΥΓΧΡΟΝΙΣΜΟΥ & ΕΛΕΓΧΟΥ ΑΓΓΕΛΙΩΝ (CAR.GR VS DATABASE)")
    print("=" * 75)

    # 1. Get DB state
    db_items = get_db_listings()
    db_ids = set(db_items.keys())
    print(f"📦 Αγγελίες στη Βάση Δεδομένων (SQLite): {len(db_ids):,}")

    # 2. Get Live Car.gr state
    live_items = scan_live_catalog_ids(workers=workers)
    live_ids = set(live_items.keys())
    
    if not live_ids:
        print("❌ Δεν βρέθηκαν ενεργές αγγελίες στο Car.gr (πιθανό προσωρινό rate limit / timeout).")
        print("💡 Δοκιμάστε ξανά σε λίγα λεπτά με: python main.py sync --fetch-missing\n")
        return

    print(f"🌐 Ενεργές Αγγελίες στο Car.gr: {len(live_ids):,}")

    # 3. Calculate Diffs
    in_both = db_ids & live_ids
    missing_from_db = live_ids - db_ids
    removed_from_car = db_ids - live_ids

    pct_synced = (len(in_both) / len(live_ids) * 100) if live_ids else 0.0

    print("\n" + "-" * 75)
    print("📊 ΑΠΟΤΕΛΕΣΜΑΤΑ ΣΥΓΚΡΙΣΗΣ:")
    print(f"  🟢 Σε Πλήρη Συγχρονισμό (Και στη Βάση και στο Car.gr): {len(in_both):,} ({pct_synced:.1f}%)")
    print(f"  🆕 Νέες / Ελλείπουσες από τη Βάση (Μόνο στο Car.gr):   {len(missing_from_db):,}")
    print(f"  🔴 Διαγραμμένες / Πουλημένες (Μόνο στη Βάση):         {len(removed_from_car):,}")
    print("-" * 75)

    # 4. Action: Fetch Missing
    if fetch_missing and missing_from_db:
        print(f"\n⚡ Αυτόματη συλλογή και αποθήκευση των {len(missing_from_db):,} ελλειπουσών αγγελιών στη βάση...")
        conn = get_connection()
        saved_count = 0
        for mid in missing_from_db:
            item_data = live_items.get(mid)
            if item_data and "raw" in item_data:
                save_listing(conn, item_data["raw"], is_deep=False)
                saved_count += 1
        conn.commit()
        conn.close()
        print(f"✅ Προστέθηκαν με επιτυχία {saved_count:,} νέες αγγελίες στη βάση!")

    # 5. Action: Mark Inactive
    if mark_inactive and removed_from_car:
        print(f"\n🏷️ Μαρκάρισμα των {len(removed_from_car):,} πουλημένων/διαγραμμένων αγγελιών ως 'ανενεργές'...")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE listings SET is_active = 0, last_verified_at = CURRENT_TIMESTAMP WHERE id = ?",
            [(rid,) for rid in removed_from_car]
        )
        conn.commit()
        conn.close()
        print(f"✅ Ολοκληρώθηκε η ενημέρωση κατάστασης (is_active = 0)!")

    # Mark active for existing
    if in_both:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.executemany(
            "UPDATE listings SET is_active = 1, last_verified_at = CURRENT_TIMESTAMP WHERE id = ?",
            [(aid,) for aid in in_both]
        )
        conn.commit()
        conn.close()

    # 6. Export Detailed CSV Report
    if export_csv:
        report_path = os.path.join(DB_DIR, "sync_audit_report.csv")
        headers = ["Listing ID", "Title", "Price", "Status in Car.gr", "Status in DB", "Sync State", "URL"]
        
        rows = []
        for mid in missing_from_db:
            info = live_items.get(mid, {})
            rows.append([mid, info.get("title", ""), info.get("price", ""), "ACTIVE", "MISSING", "🆕 NEW_IN_CAR_GR", info.get("url", "")])
            
        for rid in removed_from_car:
            info = db_items.get(rid, {})
            rows.append([rid, info.get("title", ""), info.get("price", ""), "REMOVED/SOLD", "PRESENT", "🔴 REMOVED_FROM_CAR_GR", f"https://www.car.gr/parts/view/{rid}/"])

        for bid in list(in_both)[:100]: # Sample of synced
            info = db_items.get(bid, {})
            rows.append([bid, info.get("title", ""), info.get("price", ""), "ACTIVE", "PRESENT", "🟢 IN_SYNC", f"https://www.car.gr/parts/view/{bid}/"])

        with open(report_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

        print(f"\n📄 Εξαγωγή αναφοράς διαφορών: {report_path}")

    print("\n" + "=" * 75)
    print("💡 Χρήσιμες Επιλογές:")
    print("   • Συγχρονισμός και αυτόματη προσθήκη όσων λείπουν: python main.py sync --fetch-missing")
    print("   • Μαρκάρισμα διαγραμμένων ως ανενεργές:            python main.py sync --mark-inactive")
    print("   • Πλήρης συγχρονισμός & ενημέρωση:                python main.py sync --all")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    run_sync_audit(fetch_missing=True, mark_inactive=True)
