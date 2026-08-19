import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
import sqlite3
import json
import re

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cargr_xml_generator import parse_vehicle_from_title, clean_text
from database import DB_PATH, DB_DIR

OUTPUT_PATH = os.path.join(DB_DIR, "cargr_test_5_feed.xml")

def generate_test_feed():
    print("=" * 70)
    print("🧪 ΔΗΜΙΟΥΡΓΙΑ ΔΟΚΙΜΑΣΤΙΚΟΥ XML FEED (5 ΝΕΕΣ ΑΓΓΕΛΙΕΣ / UNIQUE CODES)")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""
    SELECT id, title, raw_price, category_ids, full_description, part_numbers
    FROM listings
    WHERE full_description IS NOT NULL AND length(full_description) > 30
    ORDER BY id DESC
    LIMIT 5
    """)
    rows = c.fetchall()

    root = ET.Element("cardealer")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ET.SubElement(root, "lastupdate").text = now_iso

    classifieds_elem = ET.SubElement(root, "classifieds")

    test_prices = ["120.00", "85.00", "65.00", "190.00", "95.00"]

    for idx, row in enumerate(rows, 1):
        lid = row["id"]
        custom_code = f"AUTOEXPO-TEST-00{idx}"

        c_elem = ET.SubElement(classifieds_elem, "classified")

        # 1. <unique_id> Custom test code
        ET.SubElement(c_elem, "unique_id").text = custom_code

        # 2. <manufacturer_number>
        if row["part_numbers"]:
            pns = [p.strip() for p in row["part_numbers"].split(",") if p.strip()]
            if pns:
                ET.SubElement(c_elem, "manufacturer_number").text = pns[0]

        # 3. <title>
        title = clean_text(row["title"])
        ET.SubElement(c_elem, "title").text = title

        # 4. <description>
        desc = clean_text(row["full_description"])
        ET.SubElement(c_elem, "description").text = desc

        # 5. <category_id>
        cat_ids_str = row["category_ids"]
        leaf_id = "170"
        if cat_ids_str:
            try:
                cat_list = json.loads(cat_ids_str)
                if cat_list:
                    leaf_id = str(cat_list[-1])
            except Exception:
                pass
        ET.SubElement(c_elem, "category_id").text = leaf_id

        # 6. <price>
        ET.SubElement(c_elem, "price").text = test_prices[idx - 1]

        # Extract Vehicle Data (Make, Model, Year Range)
        make, model, y_from, y_to = parse_vehicle_from_title(title)
        if not make:
            make, model, y_from = "Ford", "Puma", 2019

        # 7. <product_make> & <product_model>
        ET.SubElement(c_elem, "product_make").text = make
        if model:
            ET.SubElement(c_elem, "product_model").text = model

        # 8. <makemodels>
        mm_elem = ET.SubElement(c_elem, "makemodels")
        node = ET.SubElement(mm_elem, "makemodel")
        ET.SubElement(node, "make").text = make
        if model:
            ET.SubElement(node, "model").text = model
        if y_from:
            ET.SubElement(node, "yearfrom").text = str(y_from)
        if y_to:
            ET.SubElement(node, "yearto").text = str(y_to)

        # 9. <photos>
        c.execute("SELECT url_max_res FROM listing_images WHERE listing_id = ? ORDER BY image_index LIMIT 6", (lid,))
        imgs = c.fetchall()
        if imgs:
            photos_elem = ET.SubElement(c_elem, "photos")
            for img in imgs:
                ET.SubElement(photos_elem, "photo").text = img["url_max_res"]

        # 10. <condition> & <condition_type>
        ET.SubElement(c_elem, "condition").text = "used"
        ET.SubElement(c_elem, "condition_type").text = "Γνήσιο"
        ET.SubElement(c_elem, "debatable").text = "true"

    conn.close()

    # Pretty print XML
    rough_string = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="    ", encoding="utf-8")

    with open(OUTPUT_PATH, "wb") as f:
        f.write(pretty_xml)

    print(f"✅ Το Δοκιμαστικό XML Feed δημιουργήθηκε: {OUTPUT_PATH}")
    print(f"📦 Περιλαμβάνει 5 αγγελίες με κωδικούς: AUTOEXPO-TEST-001 έως AUTOEXPO-TEST-005")

if __name__ == "__main__":
    generate_test_feed()
