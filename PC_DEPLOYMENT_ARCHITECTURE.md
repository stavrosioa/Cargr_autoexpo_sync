# ☁️ Αρχιτεκτονική Εξωτερικού Server Εταιρείας (Cloud / VPS Deployment)
**Πλήρης Τεχνική Σχεδίαση Φιλοξενίας σε Dedicated / Cloud Server της Autoexpo**

---

## 1. 🌐 Συνολικό Διάγραμμα Εξωτερικού Server (Cloud Infrastructure)

```mermaid
graph TD
    subgraph CLOUD ["☁️ ΕΞΩΤΕΡΙΚΟΣ SERVER ΕΤΑΙΡΕΙΑΣ (Cloud / Dedicated VPS - 24/7 Uptime)"]
        APP["🚀 Autoexpo Web &amp; API Server (HTTPS - app.autoexpo.gr)"]
        
        subgraph STORAGE ["💾 Αποθηκευτικός Χώρος Server"]
            DB1[("📦 ΒΑΣΗ 1: autoparts_db.sqlite<br>(Νέα Εισερχόμενα / Drafts)")]
            DB2[("🌐 ΒΑΣΗ 2: autoexpo_parts.db<br>(Master Car.gr 17.730 Αγγελίες)")]
            XML["📄 cargr_parts_feed.xml<br>(Επίσημο Feed Car.gr)"]
            IMG_MASTER["📂 data/<br>(105 GB Master Φωτογραφίες)"]
        end

        FEED_SRV["🌐 Direct XML Endpoint<br>https://app.autoexpo.gr/feeds/cargr_parts_feed.xml"]
        
        APP --> STORAGE
        STORAGE --> FEED_SRV
    end

    subgraph SHOP ["🏬 ΚΑΤΑΣΤΗΜΑ AUTOEXPO (Πρόσβαση από Οπουδήποτε μέσω Web)"]
        C_MGR["📱 Κινητό Manager (/mobile QR στο ράφι)"]
        C_LST["💻 PC Lister (Γραφείο / Έλεγχος &amp; Ανέβασμα)"]
        C_CAR["💻 PC Cargr Admin (Dashboard, Τιμές, Re-bumps)"]
        C_REM["🏠 Απομακρυσμένη Πρόσβαση (Από το σπίτι / Laptops)"]
    end

    subgraph CARGR ["🚗 ΠΛΑΤΦΟΡΜΑ CAR.GR"]
        CARGR_BOT["🤖 Car.gr Automated XML Ingest"]
    end

    SHOP -->|Ασφαλής Σύνδεση HTTPS (Login)| APP
    FEED_SRV -->|Απευθείας Ανάγνωση Feed| CARGR_BOT
```

---

## 2. 💎 Γιατί ο Εξωτερικός Server είναι η Καλύτερη Επιλογή:

1. **24/7/365 Αδιάλειπτη Λειτουργία:**  
   Ο server δεν κλείνει ποτέ. Δεν επηρεάζεται από διακοπές ρεύματος, κλείσιμο καταστήματος ή επανεκκινήσεις τοπικών υπολογιστών.
2. **Μόνιμο & Επίσημο URL για το Car.gr:**  
   Το XML Feed σερβίρεται απευθείας από το δικό σας εταιρικό domain:  
   👉 **`https://app.autoexpo.gr/feeds/cargr_parts_feed.xml`**  
   *(Το Car.gr το αναγνωρίζει 100% ως αυθεντικό εταιρικό feed).*
3. **Πρόσβαση από Παντού:**  
   Ο Manager φωτογραφίζει με το κινητό στο μαγαζί, ο Lister δουλεύει στο PC του, και εσείς μπορείτε να βλέπετε τα πάντα ακόμα και από το σπίτι ή το κινητό σας!
4. **Αστραπιαία Ταχύτητα & Ασφάλεια:**  
   Όλες οι ενέργειες (αλλαγές τιμών, εγκρίσεις Lister, πωλήσεις) εκτελούνται απευθείας στον Cloud Server σε κλάσματα δευτερολέπτου.

---

## 3. 📍 Πού Βρίσκεται το Κάθε Στοιχείο στον Server:

| Στοιχείο | Τοποθεσία στον Εξωτερικό Server | Περιγραφή |
| :--- | :--- | :--- |
| **Web Εφαρμογή** | `/var/www/autoexpo_manager` (ή `C:\Autoexpo`) | Η multi-user εφαρμογή με ασφαλές HTTPS πιστοποιητικό (SSL). |
| **Βάση 1 (Αποθήκη)** | `database/autoparts_db.sqlite` | Τα νέα ανταλλακτικά που φωτογραφίζει ο Manager. |
| **Βάση 2 (Master Car.gr)** | `database/autoexpo_parts.db` (213 MB) | **Και τα 17.730 ενεργά ανταλλακτικά του μαγαζιού**. |
| **Φωτογραφίες** | `data/` (105.65 GB) | Όλες οι 525.290 φωτογραφίες σε γρήγορο αποθηκευτικό χώρο (NVMe / SSD). |
| **XML Feed Endpoint** | `https://app.autoexpo.gr/feeds/...` | Το ζωντανό XML link που διαβάζει το Car.gr. |

---

## 4. 👥 Η Καθημερινή Ροή Εργασίας στο Μαγαζί:

1. **Manager (Στο Ράφι):** Ανοίγει το κινητό στο `app.autoexpo.gr`, φωτογραφίζει το ανταλλακτικό και οργανώνει τις φωτογραφίες.
2. **Lister (Στο Γραφείο):** Ανοίγει το `app.autoexpo.gr`, βλέπει τις νέες φωτογραφίες, ελέγχει τους κωδικούς (OCR), βάζει τιμή και πατάει **`[🚀 Ανέβασμα στο Car.gr]`**.
3. **Αυτόματη Ενημέρωση:** Ο Εξωτερικός Server ενημερώνει αμέσως το `cargr_parts_feed.xml`.
4. **Car.gr Sync:** Το Car.gr διαβάζει απευθείας το link του εξωτερικού server και συγχρονίζει αυτόματα!
