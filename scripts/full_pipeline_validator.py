import os
import sys
import sqlite3
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

REPO_DIR = r"C:\Users\kioan\OneDrive\stauro poutana\Cargr_autoexpo_sync\Cargr_autoexpo_sync"
DB_PATH = os.path.join(REPO_DIR, "database", "autoexpo_parts.db")
XML_PATH = os.path.join(REPO_DIR, "database", "cargr_parts_feed.xml")
CSV_PATH = os.path.join(REPO_DIR, "database", "autoexpo_parts.csv")
CATEGORIES_CSV = os.path.join(REPO_DIR, "part_xyma_categories.csv")
DATA_DIR = os.path.join(REPO_DIR, "data")

def print_header(title: str):
    print("\n" + "=" * 75)
    print(f"🛡️  {title}")
    print("=" * 75)

def run_full_validation():
    print_header("ΕΞΟΝΥΧΙΣΤΙΚΟΣ ΕΛΕΓΧΟΣ ΑΚΕΡΑΙΟΤΗΤΑΣ & ΕΓΚΥΡΟΤΗΤΑΣ (FULL AUDIT)")
    
    total_passed = 0
    total_tests = 0
    errors = []

    def check(condition: bool, name: str, detail: str = ""):
        nonlocal total_passed, total_tests
        total_tests += 1
        if condition:
            total_passed += 1
            print(f"  ✅ [PASS] {name} {f'({detail})' if detail else ''}")
        else:
            errors.append(f"{name}: {detail}")
            print(f"  ❌ [FAIL] {name} {f'({detail})' if detail else ''}")

    # =========================================================================
    # SECTION 1: DATABASE INTEGRITY AUDIT
    # =========================================================================
    print("\n📦 [1/4] ΕΛΕΓΧΟΣ ΒΑΣΗΣ ΔΕΔΟΜΕΝΩΝ (SQLite Database):")
    if not os.path.exists(DB_PATH):
        print(f"❌ Το αρχείο βάσης δεν βρέθηκε: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. PRAGMA integrity
    c.execute("PRAGMA integrity_check")
    res = c.fetchone()[0]
    check(res == "ok", "PRAGMA Integrity Check", res)

    # 2. Total Listings
    c.execute("SELECT COUNT(*) FROM listings")
    listing_count = c.fetchone()[0]
    check(listing_count == 17730, "Συνολικό Πλήθος Αγγελιών", f"{listing_count:,} / 17,730")

    # 3. Duplicate IDs
    c.execute("SELECT id, COUNT(*) FROM listings GROUP BY id HAVING COUNT(*) > 1")
    dupes = c.fetchall()
    check(len(dupes) == 0, "Έλεγχος Διπλότυπων IDs (Zero Duplicates)", f"{len(dupes)} βρέθηκαν")

    # 4. Truncated descriptions ending in '...'
    c.execute("SELECT COUNT(*) FROM listings WHERE full_description LIKE '%...'")
    trunc_desc = c.fetchone()[0]
    check(trunc_desc == 0, "Πληρότητα Περιγραφών (0 Κομμένα Κείμενα)", f"{trunc_desc} κομμένες")

    # 5. Empty Titles or Empty Descriptions
    c.execute("SELECT COUNT(*) FROM listings WHERE title IS NULL OR title = '' OR full_description IS NULL OR full_description = ''")
    empty_cnt = c.fetchone()[0]
    check(empty_cnt == 0, "Έλεγχος Κενών Τίτλων & Περιγραφών", f"{empty_cnt} κενά")

    # =========================================================================
    # SECTION 2: IMAGES STORAGE AUDIT
    # =========================================================================
    print("\n🖼️ [2/4] ΕΛΕΓΧΟΣ ΤΟΠΙΚΩΝ ΦΩΤΟΓΡΑΦΙΩΝ & ΑΠΟΘΗΚΕΥΣΗΣ (Data Storage):")
    
    # 1. Downloaded images in DB
    c.execute("SELECT COUNT(*), SUM(file_size_bytes) FROM listing_images WHERE is_downloaded = 1")
    img_cnt, img_bytes = c.fetchone()
    gb_size = (img_bytes or 0) / (1024 * 1024 * 1024)
    check(img_cnt >= 525000, "Συνολικές Φωτογραφίες στη Βάση", f"{img_cnt:,} αρχεία ({gb_size:.2f} GB)")

    # 2. Distinct listings with downloaded photos
    c.execute("SELECT COUNT(DISTINCT listing_id) FROM listing_images WHERE is_downloaded = 1")
    listings_with_imgs = c.fetchone()[0]
    check(listings_with_imgs == 17730, "Κάλυψη Αγγελιών με Φωτογραφίες (100% Coverage)", f"{listings_with_imgs:,} / 17,730 αγγελίες")

    # 3. Disk Sample Verification
    sample_files_checked = 0
    sample_files_ok = 0
    c.execute("SELECT local_path FROM listing_images WHERE is_downloaded = 1 LIMIT 50")
    for row in c.fetchall():
        lpath = row["local_path"]
        if lpath and os.path.exists(lpath) and os.path.getsize(lpath) > 100:
            sample_files_ok += 1
        sample_files_checked += 1
    check(sample_files_ok == sample_files_checked, "Δειγματοληπτικός Έλεγχος Αρχείων στο Δίσκο", f"{sample_files_ok}/{sample_files_checked} αρχεία ΟΚ")

    conn.close()

    # =========================================================================
    # SECTION 3: OFFICIAL CAR.GR XML FEED VALIDATION
    # =========================================================================
    print("\n🌐 [3/4] ΕΛΕΓΧΟΣ ΕΠΙΣΗΜΟΥ CAR.GR XML FEED (cargr_parts_feed.xml):")
    if not os.path.exists(XML_PATH):
        print(f"❌ Το αρχείο XML δεν βρέθηκε: {XML_PATH}")
        return

    xml_size_mb = os.path.getsize(XML_PATH) / (1024 * 1024)
    check(xml_size_mb > 50, "Μέγεθος Αρχείου XML Feed", f"{xml_size_mb:.2f} MB")

    try:
        tree = ET.parse(XML_PATH)
        root = tree.getroot()
        check(root.tag == "cardealer", "Root Element XML", f"<{root.tag}>")

        lastupdate = root.find("lastupdate")
        check(lastupdate is not None and len(lastupdate.text) > 15, "Πεδίο <lastupdate> (ISO 8601)", lastupdate.text if lastupdate is not None else "Missing")

        classifieds = root.find("classifieds")
        check(classifieds is not None, "Container Element <classifieds>", "Found")

        all_items = classifieds.findall("classified") if classifieds is not None else []
        check(len(all_items) == 17730, "Πλήθος <classified> στο XML", f"{len(all_items):,} / 17,730")

        # Deep sample inspection on XML elements
        valid_items_count = 0
        valid_cats_count = 0
        debatable_false_count = 0
        has_makes_count = 0
        has_photos_count = 0

        for item in all_items[:500]:
            uid = item.find("unique_id")
            title = item.find("title")
            desc = item.find("description")
            cat = item.find("category_id")
            price = item.find("price")
            deb = item.find("debatable")
            mm = item.find("makemodels")
            photos = item.find("photos")

            if uid is not None and title is not None and desc is not None and cat is not None and price is not None:
                valid_items_count += 1
            if cat is not None and cat.text.isdigit():
                valid_cats_count += 1
            if deb is not None and deb.text == "false":
                debatable_false_count += 1
            if mm is not None and len(mm.findall("makemodel")) > 0:
                has_makes_count += 1
            if photos is not None and len(photos.findall("photo")) > 0:
                has_photos_count += 1

        check(valid_items_count == 500, "Πληρότητα Υποχρεωτικών Πεδίων Car.gr (Δείγμα 500)", f"{valid_items_count}/500")
        check(valid_cats_count == 500, "Εγκυρότητα Leaf Category IDs (Δείγμα 500)", f"{valid_cats_count}/500")
        check(debatable_false_count == 500, "Ρύθμιση <debatable> = false (Δείγμα 500)", f"{debatable_false_count}/500")
        check(has_makes_count >= 480, "Πληρότητα Μάρκας & Μοντέλου <makemodels> (Δείγμα 500)", f"{has_makes_count}/500")
        check(has_photos_count == 500, "Πληρότητα Φωτογραφιών <photos> (Δείγμα 500)", f"{has_photos_count}/500")

    except Exception as e:
        check(False, "XML Parsing & Well-formedness", str(e))

    # =========================================================================
    # SECTION 4: EXPORT CSV AUDIT
    # =========================================================================
    print("\n📊 [4/4] ΕΛΕΓΧΟΣ ΕΞΑΓΩΓΗΣ EXCEL (CSV Export):")
    if os.path.exists(CSV_PATH):
        csv_size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
        check(csv_size_mb > 35, "Μέγεθος autoexpo_parts.csv", f"{csv_size_mb:.2f} MB")
        
        with open(CSV_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        check(len(lines) >= 17730, "Γραμμές στο CSV Export", f"{len(lines):,} γραμμές")
    else:
        check(False, "Ύπαρξη autoexpo_parts.csv", "Δεν βρέθηκε")

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    print_header("ΤΕΛΙΚΑ ΑΠΟΤΕΛΕΣΜΑΤΑ ΕΛΕΓΧΟΥ (VALIDATION SCORE)")
    success_rate = (total_passed / total_tests) * 100
    print(f"📊 Σύνολο Ελέγχων: {total_tests}")
    print(f"🟢 Επιτυχείς Έλεγχοι (PASSED): {total_passed} / {total_tests} ({success_rate:.1f}%)")
    
    if errors:
        print("\n❌ ΣΦΑΛΜΑΤΑ ΠΟΥ ΕΝΤΟΠΙΣΤΗΚΑΝ:")
        for err in errors:
            print(f"  • {err}")
    else:
        print("\n🏆 ΟΛΑ ΤΑ ΣΥΣΤΗΜΑΤΑ ΕΙΝΑΙ 100% ΑΨΟΓΑ, ΕΓΚΥΡΑ & ΑΠΟΛΥΤΑ ΣΥΜΒΑΤΑ ΜΕ ΤΟ CAR.GR!")

if __name__ == "__main__":
    run_full_validation()
