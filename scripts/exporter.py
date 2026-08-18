import os
import sys

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
import csv
import json
import sqlite3
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, DB_PATH, DB_DIR, DATA_DIR

def export_to_csv(output_path: Optional[str] = None):
    if not output_path:
        output_path = os.path.join(DB_DIR, "autoexpo_parts.csv")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        l.id,
        l.title,
        l.descriptive_title,
        l.price,
        l.raw_price,
        l.category,
        l.condition,
        l.part_numbers,
        l.makes_models_summary,
        l.keywords,
        l.views_count,
        l.parked_count,
        l.short_description,
        l.full_description,
        l.address,
        l.latitude,
        l.longitude,
        l.created_at,
        l.modified_at,
        l.url,
        l.photo_count,
        l.data_folder,
        GROUP_CONCAT(img.url_max_res, ' | ') as image_urls
    FROM listings l
    LEFT JOIN listing_images img ON l.id = img.listing_id
    GROUP BY l.id
    ORDER BY l.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("⚠️ Δεν υπάρχουν δεδομένα στη βάση για εξαγωγή.")
        return

    headers = [
        "Ad ID", "Title", "Descriptive Title", "Price", "Raw Price (€)",
        "Category", "Condition", "OEM / Factory Codes", "Compatible Makes/Models & Years",
        "Keywords / Search Tags", "Views Count", "Parked Count",
        "Short Description", "Full Description", "Address", "Latitude", "Longitude",
        "Created At", "Modified At", "Car.gr URL", "Photo Count", "Data Folder", "Max-Res Image URLs"
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(list(r))

    print(f"✅ Εξαγωγή CSV ολοκληρώθηκε: {output_path} ({len(rows):,} εγγραφές)")

def export_to_json(output_path: Optional[str] = None):
    if not output_path:
        output_path = os.path.join(DB_DIR, "autoexpo_parts.json")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM listings ORDER BY id DESC")
    listings = cursor.fetchall()

    results = []
    for l in listings:
        item = dict(l)
        lid = item["id"]

        # Images
        cursor.execute("SELECT image_index, url_max_res, local_path, is_downloaded FROM listing_images WHERE listing_id = ? ORDER BY image_index", (lid,))
        item["images"] = [dict(img) for img in cursor.fetchall()]

        # Compatible vehicles
        cursor.execute("SELECT make, model, year_from, year_to FROM compatible_vehicles WHERE listing_id = ?", (lid,))
        item["compatible_vehicles"] = [dict(v) for v in cursor.fetchall()]

        # Tags
        cursor.execute("SELECT tag FROM listing_tags WHERE listing_id = ?", (lid,))
        item["tags"] = [r[0] for r in cursor.fetchall()]

        if item.get("category_ids"):
            try:
                item["category_ids"] = json.loads(item["category_ids"])
            except Exception:
                pass
        if item.get("categories_json"):
            try:
                item["categories_list"] = json.loads(item["categories_json"])
            except Exception:
                pass

        results.append(item)

    conn.close()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"✅ Εξαγωγή JSON ολοκληρώθηκε: {output_path} ({len(results):,} εγγραφές)")

if __name__ == "__main__":
    export_to_csv()
    export_to_json()
