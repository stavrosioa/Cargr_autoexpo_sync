import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(PROJECT_ROOT, "database")
DB_PATH = os.path.join(DB_DIR, "autoexpo_parts.db")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

os.makedirs(DB_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str = DB_PATH):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Listings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY,
        title TEXT,
        descriptive_title TEXT,
        price TEXT,
        raw_price REAL,
        price_debatable INTEGER DEFAULT 0,
        without_vat INTEGER DEFAULT 0,
        category TEXT,
        category_ids TEXT,
        categories_json TEXT,
        short_description TEXT,
        full_description TEXT,
        condition TEXT,
        is_new INTEGER DEFAULT 0,
        damaged INTEGER DEFAULT 0,
        part_numbers TEXT,
        makes_models_summary TEXT,
        keywords TEXT,
        views_count INTEGER DEFAULT 0,
        parked_count INTEGER DEFAULT 0,
        seller_name TEXT,
        seller_user_id INTEGER,
        address TEXT,
        address_long TEXT,
        latitude REAL,
        longitude REAL,
        created_at TEXT,
        modified_at TEXT,
        url TEXT,
        seo_url TEXT,
        photo_count INTEGER DEFAULT 0,
        data_folder TEXT,
        is_deep_scraped INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        last_verified_at DATETIME,
        raw_json TEXT,
        scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Auto-migrate if table existed without new columns
    try:
        cursor.execute("ALTER TABLE listings ADD COLUMN is_active INTEGER DEFAULT 1;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE listings ADD COLUMN last_verified_at DATETIME;")
    except Exception:
        pass

    # 2. Compatible Vehicles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compatible_vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        make TEXT,
        model TEXT,
        year_from INTEGER,
        year_to INTEGER,
        FOREIGN KEY (listing_id) REFERENCES listings (id) ON DELETE CASCADE
    );
    """)

    # 3. Images Table (High-Res 1024x768)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listing_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        image_index INTEGER,
        url_max_res TEXT,
        url_medium TEXT,
        local_path TEXT,
        is_downloaded INTEGER DEFAULT 0,
        file_size_bytes INTEGER DEFAULT 0,
        downloaded_at TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings (id) ON DELETE CASCADE,
        UNIQUE(listing_id, image_index)
    );
    """)

    # 4. Tags Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listing_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER,
        tag TEXT,
        FOREIGN KEY (listing_id) REFERENCES listings (id) ON DELETE CASCADE,
        UNIQUE(listing_id, tag)
    );
    """)

    # 5. Scrape Progress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_progress (
        page_num INTEGER PRIMARY KEY,
        status TEXT,
        items_found INTEGER,
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(raw_price);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_cat ON listings(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_part ON listings(part_numbers);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_compat_make ON compatible_vehicles(make);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_compat_model ON compatible_vehicles(model);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_listing ON listing_images(listing_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_downloaded ON listing_images(is_downloaded);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON listing_tags(tag);")

    conn.commit()
    conn.close()

def save_listing(conn: sqlite3.Connection, item: Dict[str, Any], is_deep: bool = False):
    cursor = conn.cursor()

    lid = item.get("id")
    if not lid:
        return

    title = item.get("title") or ""
    descriptive_title = item.get("descriptiveTitle") or title
    
    price_obj = item.get("price")
    if isinstance(price_obj, dict):
        price = price_obj.get("value") or ""
        raw_price = price_obj.get("extra", {}).get("rawPrice")
        without_vat = 1 if price_obj.get("extra", {}).get("withoutVat") else 0
        price_debatable = 1 if price_obj.get("extra", {}).get("debatable") else 0
    else:
        price = str(price_obj or "")
        raw_price = item.get("rawPrice")
        without_vat = 1 if item.get("withoutVat") else 0
        price_debatable = 1 if item.get("priceDebatable") else 0

    category = item.get("category") or ""
    category_ids = json.dumps(item.get("categoryIds") or [])
    categories_json = json.dumps(item.get("categoriesList") or [])
    
    desc_obj = item.get("description")
    if isinstance(desc_obj, dict):
        full_desc = desc_obj.get("content") or ""
    else:
        full_desc = str(desc_obj or item.get("fullDescription") or item.get("shortDescription") or "")
    short_desc = item.get("shortDescription") or full_desc
    
    condition = item.get("condition") or ("Καινούργιο" if item.get("isNew") else "Μεταχειρισμένο (Γνήσιο)")
    is_new = 1 if item.get("isNew") else 0
    damaged = 1 if item.get("damaged") else 0
    
    part_numbers = item.get("partNumbers") or item.get("part_number") or ""
    makes_models_summary = item.get("makesModelsSummary") or ""
    keywords_str = item.get("keywords") or ""
    
    views_count = item.get("views") if isinstance(item.get("views"), int) else 0
    parked_count = item.get("parked") if isinstance(item.get("parked"), int) else 0

    seller = item.get("seller") or {}
    seller_name = seller.get("name") if isinstance(seller, dict) else "AUTOEXPO"
    seller_user_id = item.get("userId")
    
    address = item.get("address") or ""
    address_long = item.get("addressLong") or address
    geo = item.get("geolocation") or {}
    lat, lon = None, None
    if isinstance(geo, dict):
        g_inner = geo.get("geolocation") or {}
        lat = g_inner.get("lat")
        lon = g_inner.get("lon")

    created_at = item.get("created") or ""
    modified_at = item.get("modified") or ""
    
    seo_url = item.get("seoUrl") or ""
    url = f"https://autoexpo.car.gr/parts/view/{lid}/" if lid else ""
    
    raw_json = json.dumps(item, ensure_ascii=False)
    data_folder = os.path.join(DATA_DIR, str(lid))
    
    # Extract photos
    thumbs_patterns = item.get("thumbsPatterns") or {}
    urls_list = []
    if isinstance(thumbs_patterns, dict) and "urls" in thumbs_patterns:
        urls_list = thumbs_patterns["urls"]
    elif isinstance(item.get("thumbs"), dict) and "urls" in item["thumbs"]:
        urls_list = item["thumbs"]["urls"]
    elif isinstance(item.get("photos"), dict) and "native" in item["photos"]:
        native_photos = item["photos"]["native"]
        if isinstance(native_photos, list):
            urls_list = [f"{p.get('host', 'https://static.car.gr')}{p.get('sizes', {}).get('b')}" for p in native_photos if p.get('sizes')]
        
    photo_count = len(urls_list)

    cursor.execute("""
    INSERT INTO listings (
        id, title, descriptive_title, price, raw_price, price_debatable, without_vat,
        category, category_ids, categories_json, short_description, full_description, condition,
        is_new, damaged, part_numbers, makes_models_summary, keywords, views_count, parked_count,
        seller_name, seller_user_id, address, address_long, latitude, longitude,
        created_at, modified_at, url, seo_url, photo_count, data_folder, is_deep_scraped, raw_json
    ) VALUES (
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?
    )
    ON CONFLICT(id) DO UPDATE SET
        title = excluded.title,
        descriptive_title = excluded.descriptive_title,
        price = excluded.price,
        raw_price = excluded.raw_price,
        category = excluded.category,
        category_ids = excluded.category_ids,
        categories_json = CASE WHEN excluded.categories_json != '[]' THEN excluded.categories_json ELSE listings.categories_json END,
        short_description = excluded.short_description,
        full_description = excluded.full_description,
        condition = excluded.condition,
        part_numbers = CASE WHEN excluded.part_numbers != '' THEN excluded.part_numbers ELSE listings.part_numbers END,
        makes_models_summary = CASE WHEN excluded.makes_models_summary != '' THEN excluded.makes_models_summary ELSE listings.makes_models_summary END,
        keywords = CASE WHEN excluded.keywords != '' THEN excluded.keywords ELSE listings.keywords END,
        modified_at = excluded.modified_at,
        photo_count = excluded.photo_count,
        data_folder = excluded.data_folder,
        is_deep_scraped = CASE WHEN excluded.is_deep_scraped = 1 THEN 1 ELSE listings.is_deep_scraped END,
        raw_json = excluded.raw_json
    """, (
        lid, title, descriptive_title, price, raw_price, price_debatable, without_vat,
        category, category_ids, categories_json, short_desc, full_desc, condition,
        is_new, damaged, part_numbers, makes_models_summary, keywords_str, views_count, parked_count,
        seller_name, seller_user_id, address, address_long, lat, lon,
        created_at, modified_at, url, seo_url, photo_count, data_folder, 1 if is_deep else 0, raw_json
    ))

    # Save to data/<listing_id>/details.json as well
    try:
        os.makedirs(data_folder, exist_ok=True)
        with open(os.path.join(data_folder, "details.json"), "w", encoding="utf-8") as f:
            f.write(raw_json)
    except Exception:
        pass

    # Images
    for idx, pattern_url in enumerate(urls_list):
        max_res = pattern_url.replace("{size}", "b") if "{size}" in pattern_url else pattern_url.replace("_m.jpg", "_b.jpg").replace("_n.jpg", "_b.jpg")
        med_res = pattern_url.replace("{size}", "m") if "{size}" in pattern_url else pattern_url
        
        cursor.execute("""
        INSERT INTO listing_images (listing_id, image_index, url_max_res, url_medium)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(listing_id, image_index) DO UPDATE SET
            url_max_res = excluded.url_max_res,
            url_medium = excluded.url_medium
        """, (lid, idx, max_res, med_res))

    # Vehicles compatibility
    vehicles = item.get("vehicles") or item.get("for_makemodels") or []
    if vehicles and isinstance(vehicles, list):
        cursor.execute("DELETE FROM compatible_vehicles WHERE listing_id = ?", (lid,))
        for v in vehicles:
            if isinstance(v, dict):
                cursor.execute("""
                INSERT INTO compatible_vehicles (listing_id, make, model, year_from, year_to)
                VALUES (?, ?, ?, ?, ?)
                """, (lid, v.get("make"), v.get("model"), v.get("yearFrom"), v.get("yearTo")))

    # Tags / Keywords
    tags = item.get("tags") or []
    if tags and isinstance(tags, list):
        cursor.execute("DELETE FROM listing_tags WHERE listing_id = ?", (lid,))
        for t in tags:
            tag_val = t.get("value") if isinstance(t, dict) else str(t)
            if tag_val and tag_val.strip():
                cursor.execute("""
                INSERT OR IGNORE INTO listing_tags (listing_id, tag)
                VALUES (?, ?)
                """, (lid, tag_val.strip()))

def mark_page_completed(conn: sqlite3.Connection, page_num: int, items_found: int):
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scrape_progress (page_num, status, items_found)
    VALUES (?, 'completed', ?)
    ON CONFLICT(page_num) DO UPDATE SET
        status = 'completed',
        items_found = excluded.items_found,
        processed_at = CURRENT_TIMESTAMP
    """, (page_num, items_found))
    conn.commit()

def get_completed_pages(conn: sqlite3.Connection) -> set:
    cursor = conn.cursor()
    cursor.execute("SELECT page_num FROM scrape_progress WHERE status = 'completed'")
    return set(row[0] for row in cursor.fetchall())

def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT id) FROM listings")
    total_listings, distinct_ids = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM listings WHERE is_deep_scraped = 1")
    deep_scraped = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listing_images")
    total_images = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listing_images WHERE is_downloaded = 1")
    downloaded_images = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(DISTINCT page_num) FROM scrape_progress WHERE status = 'completed'")
    completed_pages = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM compatible_vehicles")
    total_compat = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM listing_tags")
    total_tags = cursor.fetchone()[0]

    return {
        "total_listings": total_listings,
        "distinct_ids": distinct_ids,
        "deep_scraped": deep_scraped,
        "total_images": total_images,
        "downloaded_images": downloaded_images,
        "completed_pages": completed_pages,
        "total_compat": total_compat,
        "total_tags": total_tags
    }
