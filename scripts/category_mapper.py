import csv
import os
import sys
import re

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

REPO_DIR = r"C:\Users\kioan\OneDrive\stauro poutana\Cargr_autoexpo_sync\Cargr_autoexpo_sync"
CSV_PATH = os.path.join(REPO_DIR, "part_xyma_categories.csv")

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    replacements = {
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'ϊ': 'ι', 'ΐ': 'ι', 'ϋ': 'υ', 'ΰ': 'υ'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()

class CategoryMapper:
    def __init__(self, csv_path: str = CSV_PATH):
        self.categories_by_id = {}
        self.categories_by_name = {}
        self.categories_by_path = {}
        self.load_categories(csv_path)

    def load_categories(self, csv_path: str):
        if not os.path.exists(csv_path):
            print(f"⚠️ Category CSV not found: {csv_path}")
            return

        with open(csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat_id = int(row["id"])
                name = row["name"].strip()
                path = row["path"].strip()
                norm_name = normalize_text(name)
                norm_path = normalize_text(path)

                self.categories_by_id[cat_id] = {
                    "id": cat_id,
                    "name": name,
                    "path": path,
                    "has_make": row.get("has_make", "True").lower() == "true"
                }
                self.categories_by_name[norm_name] = cat_id
                self.categories_by_path[norm_path] = cat_id

        print(f"✅ Φορτώθηκαν {len(self.categories_by_id):,} επίσημες κατηγορίες Car.gr από το part_xyma_categories.csv!")

    def map_category(self, category_text: str, fallback_id: int = 170) -> int:
        if not category_text:
            return fallback_id

        norm = normalize_text(category_text)

        # 1. Exact path match
        if norm in self.categories_by_path:
            return self.categories_by_path[norm]

        # 2. Exact leaf name match
        parts = [p.strip() for p in category_text.split("»") if p.strip()]
        if parts:
            leaf_norm = normalize_text(parts[-1])
            if leaf_norm in self.categories_by_name:
                return self.categories_by_name[leaf_norm]

        # 3. Partial match against leaf names
        for norm_name, cat_id in self.categories_by_name.items():
            if norm_name and (norm_name in norm or norm in norm_name):
                return cat_id

        return fallback_id

if __name__ == "__main__":
    mapper = CategoryMapper()
    test_cases = [
        "Ανάρτηση & Τιμόνι » Αμορτισέρ",
        "Ανάρτηση & Τιμόνι » Ημιαξόνια",
        "Αμάξωμα - Είδη Φανοποιίας » Τραβέρσα",
        "Μηχανικά » Κινητήρες / Μοτέρ",
        "Φανοποιία » Φανάρια Εμπρός",
        "Κρεμαγιέρα",
        "Ψαλίδια",
        "Ζαντολάστιχα"
    ]
    print("\n=== ΔΟΚΙΜΗ ΑΝΤΙΣΤΟΙΧΙΣΗΣ ΚΑΤΗΓΟΡΙΩΝ ===")
    for tc in test_cases:
        cid = mapper.map_category(tc)
        cat_info = mapper.categories_by_id.get(cid, {})
        print(f"• \"{tc}\" -> Category ID: {cid} ({cat_info.get('name')})")
