import os
import sys

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

import sqlite3
import json
import re
from curl_cffi import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, DB_PATH, DATA_DIR
from scraper import extract_nuxt_data, BASE_URL, HEADERS

def verify_dataset():
    print("=" * 70)
    print("🔍 ΕΛΕΓΧΟΣ ΠΛΗΡΟΤΗΤΑΣ & ΜΟΝΑΔΙΚΟΤΗΤΑΣ ΑΡΙΘΜΩΝ ΑΓΓΕΛΙΑΣ CAR.GR")
    print("=" * 70)

    # 1. Fetch live metadata from Car.gr
    print("\n1️⃣  Ζωντανός Έλεγχος Στόχου από το Car.gr...")
    try:
        session = requests.Session(impersonate="safari17_0")
        resp = session.get(BASE_URL, headers=HEADERS, timeout=15)
        live_total = 17730
        live_pages = 739
        
        if resp.status_code == 200:
            nuxt = extract_nuxt_data(resp.text)
            if nuxt:
                p_info = nuxt.get("state", {}).get("classifieds", {}).get("search", {}).get("pagination", {})
                if "total" in p_info:
                    live_total = p_info["total"]
                    per_page = p_info.get("perPage", 24)
                    live_pages = (live_total + per_page - 1) // per_page
        
        print(f"   • Τρέχον σύνολο ενεργών αγγελιών στο Car.gr: {live_total:,}")
        print(f"   • Συνολικές σελίδες καταλόγου: {live_pages:,}")
    except Exception as e:
        print(f"   ⚠️ Αδυναμία ζωντανού ελέγχου: {e}")
        live_total = 17730
        live_pages = 739

    # 2. Database Checks
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Η βάση δεδομένων δεν υπάρχει ακόμη στο: {DB_PATH}")
        print("   Εκτελέστε πρώτα: python main.py scrape")
        return

    conn = get_connection()
    cursor = conn.cursor()

    print("\n2️⃣  Έλεγχος Δεδομένων & Μοναδικότητας IDs στη Βάση SQLite...")
    
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT id) FROM listings")
    total_rows, distinct_ids = cursor.fetchone()

    cursor.execute("SELECT id, COUNT(*) FROM listings GROUP BY id HAVING COUNT(*) > 1")
    duplicate_rows = cursor.fetchall()
    duplicate_count = len(duplicate_rows)

    cursor.execute("SELECT MIN(id), MAX(id) FROM listings")
    min_id, max_id = cursor.fetchone()

    cursor.execute("SELECT COUNT(DISTINCT page_num) FROM scrape_progress WHERE status = 'completed'")
    db_pages = cursor.fetchone()[0]

    cursor.execute("SELECT page_num FROM scrape_progress WHERE status = 'completed'")
    completed_set = set(r[0] for r in cursor.fetchall())
    missing_pages = [p for p in range(1, live_pages + 1) if p not in completed_set]

    cursor.execute("SELECT COUNT(*) FROM listing_images")
    total_images = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listing_images WHERE is_downloaded = 1")
    downloaded_images = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listings WHERE title IS NULL OR title = ''")
    empty_titles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listings WHERE photo_count = 0")
    zero_photos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listings WHERE is_deep_scraped = 1")
    deep_scraped = cursor.fetchone()[0]

    conn.close()

    # Count actual folders in data/
    existing_folders = 0
    if os.path.exists(DATA_DIR):
        existing_folders = len([f for f in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, f)) and not f.startswith('.')])

    print(f"   • Συνολικές εγγραφές στη βάση: {total_rows:,}")
    print(f"   • Μοναδικοί Αριθμοί Αγγελίας (Distinct IDs): {distinct_ids:,} / {live_total:,} ({distinct_ids/live_total*100:.1f}%)")
    print(f"   • Ξεχωριστοί Φάκελοι Αγγελιών στο data/: {existing_folders:,}")
    
    if duplicate_count == 0 and total_rows == distinct_ids:
        print(f"   ✅ Έλεγχος Διπλοτύπων: 0 διπλότυπα! Κάθε αγγελία έχει 100% μοναδικό αριθμό ID.")
    else:
        print(f"   ❌ Εντοπίστηκαν {duplicate_count} διπλότυπα IDs!")

    if min_id and max_id:
        print(f"   • Εύρος Αριθμών Αγγελίας (ID range): #{min_id:,} έως #{max_id:,}")

    print(f"   • Σελίδες καταλόγου που σαρώθηκαν: {db_pages:,} / {live_pages:,}")
    print(f"   • High-Res Φωτογραφίες (URLs): {total_images:,}")
    print(f"   • Φωτογραφίες αποθηκευμένες στο δίσκο: {downloaded_images:,}")

    # 3. Gap Analysis
    print("\n3️⃣  Ανάλυση Κενών & Ακεραιότητας Σελίδων:")
    if not missing_pages:
        print("   ✅ Όλες οι 739 σελίδες σαρώθηκαν χωρίς κανένα κενό!")
    else:
        print(f"   ⚠️ Υπάρχουν {len(missing_pages)} σελίδες που δεν έχουν συλλεχθεί ακόμη:")
        print(f"      Σελίδες: {missing_pages[:15]}{'...' if len(missing_pages) > 15 else ''}")
        print("      (Εκτελέστε 'python main.py scrape' για να συλλέξει αυτόματα μόνο όσες λείπουν).")

    print("\n4️⃣  Έλεγχος Ποιότητας Πεδίων:")
    print(f"   • Αγγελίες χωρίς τίτλο: {empty_titles} (0 αναμενόμενο)")
    print(f"   • Αγγελίες χωρίς φωτογραφίες: {zero_photos}")
    print(f"   • Αγγελίες με βαθιά ανάλυση OEM/Συμβατότητας: {deep_scraped:,}")

    # Final Verdict
    print("\n" + "=" * 70)
    if distinct_ids >= live_total and not missing_pages and duplicate_count == 0:
        print(f"🎉 ΕΠΙΤΥΧΙΑ: ΕΧΟΥΝ ΣΥΛΛΕΧΘΕΙ ΚΑΙ ΟΙ {distinct_ids:,} ΑΓΓΕΛΙΕΣ ΜΕ ΔΙΑΦΟΡΕΤΙΚΟ ΑΡΙΘΜΟ ΑΓΓΕΛΙΑΣ!")
        print(f"   Όλα τα δεδομένα βρίσκονται οργανωμένα στους φακέλους data/ και στη βάση database/autoexpo_parts.db.")
    else:
        diff = live_total - distinct_ids
        print(f"⏳ ΚΑΤΑΣΤΑΣΗ: Έχουν συλλεχθεί {distinct_ids:,} μοναδικές αγγελίες από {live_total:,} (Απομένουν {max(0, diff):,}).")
        print("💡 Για να ολοκληρώσετε το 100%, εκτελέστε: python main.py scrape")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    verify_dataset()
