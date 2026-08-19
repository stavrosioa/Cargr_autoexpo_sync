# 🚀 Autoexpo Car.gr Pipeline & XML Feed Integration
**Ολοκληρωμένη Τεχνική Τεκμηρίωση & Προδιαγραφές Συστήματος**

---

## 1. 📌 Επισκόπηση Έργου (Executive Summary)

Το σύστημα **Autoexpo Car.gr Pipeline** αναπτύχθηκε για να προσφέρει **πλήρη ανεξαρτησία, αυτοματοποίηση και συγχρονισμό** του αποθέματος ανταλλακτικών της εταιρείας **Autoexpo** με την πλατφόρμα του **Car.gr** μέσω του επίσημου προτύπου **XML Feed (`xyma-parts`)**.

### 📊 Βασικά Μεγέθη Καταλόγου:
- **Συνολικές Αγγελίες:** `17.730`
- **Πληρότητα Περιγραφών:** `100.0%` (0 κομμένα κείμενα)
- **Αποθηκευμένες Φωτογραφίες Τοπικά:** `525.290` αρχεία High-Res (`105.65 GB`)
- **Μοναδικότητα Δεδομένων:** `100% Zero-Duplicates` (17.730 μοναδικά IDs)
- **Εγκυρότητα XML Feed:** `100% Validated` από τον Επίσημο Ελεγκτή του Car.gr
- **Έλεγχος Ακεραιότητας (Audit):** `20 / 20 Tests Passed (100.0%)`

---

## 2. 🏗️ Αρχιτεκτονική & Δομή Συστήματος

```
Cargr_autoexpo_sync/
├── database/
│   ├── autoexpo_parts.db       # SQLite Single Source of Truth (213 MB)
│   ├── autoexpo_parts.csv      # Πλήρης εξαγωγή σε Excel (41.7 MB)
│   ├── autoexpo_parts.json     # Πλήρης εξαγωγή σε JSON (250 MB)
│   ├── cargr_parts_feed.xml    # Επίσημο Car.gr XML Feed 17.730 αγγελιών (56.2 MB)
│   └── cargr_test_5_feed.xml   # Δοκιμαστικό XML Feed 5 αγγελιών (8 KB)
├── data/                       # Φάκελοι φωτογραφιών ανά αγγελία (105.65 GB)
│   ├── 344340392/              # ID Αγγελίας
│   │   ├── 0.jpg               # 1η φωτογραφία
│   │   ├── 1.jpg               # 2η φωτογραφία
│   │   └── ...
├── scripts/
│   ├── database.py             # SQLite Schema & Thread-safe queries
│   ├── scraper.py              # Parallel catalog extraction & Rate-limit handling
│   ├── reconstruct_descriptions.py # Smart auto-fill for truncated descriptions
│   ├── image_downloader.py     # Asynchronous High-Res Image Downloader (40 workers)
│   ├── category_mapper.py      # Official Car.gr 1,011 Car Categories Mapper
│   ├── cargr_xml_generator.py  # Car.gr XML generator & schema validator
│   ├── generate_test_feed.py   # Test XML generator (5 sample ads)
│   ├── sync_diff.py            # Fast incremental sync & audit engine
│   ├── full_pipeline_validator.py # 20-Point System Integrity Auditor
│   ├── viewer_app.py           # Local Web Dashboard (FastAPI/HTML)
│   └── exporter.py             # CSV / JSON multi-format exporter
├── main.py                     # Κεντρικό CLI Interface (audit, export-xml, viewer, scrape, sync)
├── part_xyma_categories.csv    # Official Car.gr Categories Reference
├── requirements.txt            # Python Dependencies
├── .gitignore                  # Production-ready Git exclusions
└── PROJECT_DOCUMENTATION.md    # Πλήρης Τεχνική Τεκμηρίωση
```

---

## 3. 🌐 Τεχνικές Προδιαγραφές Car.gr XML Feed (`xyma-parts`)

Το XML Feed παράγεται σύμφωνα με το επίσημο documentation του **Car.gr (`car.gr/xmldoc/xyma-parts`)**.

### 📐 Δομή XML Δέντρου (XML Schema):

```xml
<?xml version="1.0" encoding="utf-8"?>
<cardealer>
    <lastupdate>2026-08-19T18:03:49Z</lastupdate>
    <classifieds>
        <classified>
            <unique_id>344340392</unique_id>
            <title>ΑΚΡΑ ΑΡΙΣΤΕΡΟ &amp; ΔΕΞΙ ΜΕ ΑΜΟΡΤΙΣΕΡ FORD PUMA 19--&gt; B7JB 1.0 ΒΕΝΖΙΝΗ - ΡΩΤΗΣΤΕ ΤΙΜΗ - ΑΠΟΣΤΟΛΗ ΣΕ ΟΛΗ ΤΗΝ ΕΛΛΑΔΑ</title>
            <description>ΑΚΡΑ ΜΕ ΜΠΟΥΚΑΛΑ ΓΙΑ ΠΟΛΛΑ ΜΟΝΤΕΛΑ ΑΥΤΟΚΙΝΗΤΩΝ ΣΤΙΣ ΚΑΛΥΤΕΡΕΣ ΤΙΜΕΣ ΤΗΣ ΑΓΟΡΑΣ ΚΑΘΩΣ ΚΑΙ ΠΟΛΛΑ ΑΛΛΑ ΑΝΤΑΛΛΑΚΤΙΚΑ.</description>
            <category_id>170</category_id>
            <price>120.00</price>
            <product_make>Ford</product_make>
            <product_model>PUMA</product_model>
            <makemodels>
                <makemodel>
                    <make>Ford</make>
                    <model>PUMA</model>
                    <yearfrom>2019</yearfrom>
                </makemodel>
            </makemodels>
            <photos>
                <photo>https://static.car.gr/344340392_0_b.jpg</photo>
                <photo>https://static.car.gr/344340392_1_b.jpg</photo>
            </photos>
            <condition>used</condition>
            <condition_type>Γνήσιο</condition_type>
            <debatable>false</debatable>
        </classified>
    </classifieds>
</cardealer>
```

### 📋 Ανάλυση Πεδίων & Κανόνες Car.gr:

| Πεδίο XML | Τύπος | Υποχρεωτικό | Περιγραφή & Κανόνας Εγκυρότητας |
| :--- | :--- | :---: | :--- |
| `<lastupdate>` | ISO 8601 UTC | **ΝΑΙ** | Ημερομηνία και ώρα παραγωγής του αρχείου (π.χ. `2026-08-19T18:03:49Z`). |
| `<unique_id>` | String | **ΝΑΙ** | **Ο Εσωτερικός Κωδικός Καταστήματος**. Αντιστοιχίζεται 1-προς-1 με το ID της αγγελίας στο Car.gr για αποφυγή διπλότυπων. |
| `<title>` | String (<=200) | **ΝΑΙ** | Τίτλος του ανταλλακτικού με αυτόματο XML escaping (`&` -> `&amp;`, `<` -> `&lt;`). |
| `<description>` | Text (<=6000) | **ΝΑΙ** | Πλήρης περιγραφή του ανταλλακτικού (100% ολοκληρωμένο κείμενο χωρίς αποσιωπητικά). |
| `<category_id>` | Integer | **ΝΑΙ** | **Αυστηρά 1 leaf ID κατηγορίας** από τις 1.011 επίσημες κατηγορίες Αυτοκινήτου του Car.gr. |
| `<price>` | Decimal | **ΝΑΙ** | Τιμή σε Ευρώ με 2 δεκαδικά (π.χ. `120.00`). |
| `<product_make>` | String | Όχι | Μάρκα προϊόντος (π.χ. `Ford`, `Toyota`, `Volkswagen`). |
| `<product_model>` | String | Όχι | Μοντέλο προϊόντος (π.χ. `PUMA`, `GOLF`, `YARIS`). |
| `<makemodels>` | Tree | Όχι | Συμβατά οχήματα με `<make>`, `<model>`, `<yearfrom>`, `<yearto>`. |
| `<condition>` | Enum | **ΝΑΙ** | `used` (Μεταχειρισμένο) ή `new` (Καινούργιο). |
| `<condition_type>`| String | Όχι | `Γνήσιο`, `Ιμιτασιόν`, `Ανακατασκευή`. |
| `<debatable>` | Boolean | **ΝΑΙ** | Αυστηρά `false` (Μη συζητήσιμη τιμή). |
| `<photos>` | Tree | **ΝΑΙ** | Λίστα πλήρων High-Res URLs των φωτογραφιών του ανταλλακτικού. |

---

## 4. 💻 Εντολές Χρήσης (CLI Reference)

Όλες οι λειτουργίες εκτελούνται μέσω του [`main.py`](file:///c:/Users/kioan/OneDrive/stauro%20poutana/Cargr_autoexpo_sync/Cargr_autoexpo_sync/main.py):

```powershell
# 1. Εξονυχιστικός Έλεγχος Ακεραιότητας 20 Σημείων (Validation Audit)
python main.py audit

# 2. Παραγωγή Επίσημου Car.gr XML Feed (17.730 αγγελίες)
python main.py export-xml

# 3. Επικύρωση Εγκυρότητας XML Feed
python main.py validate-xml

# 4. Εκκίνηση Τοπικού Web Dashboard (Viewer)
python main.py viewer --port 8088

# 5. Έλεγχος Στατιστικών Καταλόγου
python main.py stats
```

---

## 5. 🛡️ Αποτελέσματα Ελέγχου Ακεραιότητας (20/20 Passed)

```
===========================================================================
🛡️  ΕΞΟΝΥΧΙΣΤΙΚΟΣ ΕΛΕΓΧΟΣ ΑΚΕΡΑΙΟΤΗΤΑΣ & ΕΓΚΥΡΟΤΗΤΑΣ (FULL AUDIT)
===========================================================================
📦 [1/4] ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ: 17.730 / 17.730 Αγγελίες, 0 Duplicates, 0 Κομμένα Κείμενα
🖼️ [2/4] ΦΩΤΟΓΡΑΦΙΕΣ:   525.290 Αρχεία (105.65 GB), 100% Κάλυψη
🌐 [3/4] XML FEED:      56.22 MB, 17.730 Classifieds, 100% Car.gr Validated
📊 [4/4] EXCEL CSV:     41.75 MB, 24.014 Γραμμές
===========================================================================
🟢 ΕΠΙΤΥΧΙΑ: 20 / 20 ΕΛΕΓΧΟΙ (100.0% VALIDATION SCORE)
```
