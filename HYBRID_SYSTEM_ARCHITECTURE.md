# 🏛️ Πλήρης Υβριδική Αρχιτεκτονική: Local Shop Server ➡️ Cloud Server ➡️ Car.gr
**Η Ακριβής Τοπολογία Συστημάτων, Βάσεων Δεδομένων & Ρόλων της Autoexpo**

---

## 1. 🌐 Το Συνολικό Διάγραμμα Υβριδικής Αρχιτεκτονικής (Hybrid Cloud Topology)

```mermaid
graph TD
    subgraph SHOP ["🏬 1. ΤΟΠΙΚΟΣ SERVER ΣΤΟ ΜΑΓΑΖΙ (Local Server-Magazi)"]
        MGR["📸 Manager: Φωτογραφίζει με κινητό (/mobile QR στο LAN)<br>• Οργανώνει τοπικούς φακέλους &amp; εικόνες"]
        DB_LOCAL[("📦 ΒΑΣΗ ΜΑΓΑΖΙΟΥ (autoparts_db.sqlite)<br>• Τα νέα ανταλλακτικά που φωτογραφίζονται")]
        IMG_LOCAL["📂 Τοπικοί Φάκελοι Φωτογραφιών"]
        
        LST["📝 Lister: Βλέπει τι έφτιαξε ο Manager<br>• OCR, OEM κωδικοί, μάρκα, μοντέλο, τιμή<br>• 🚀 ΠΑΤΑΕΙ: 'Ανέβασμα στο Car.gr'"]
        
        MGR --> DB_LOCAL
        MGR --> IMG_LOCAL
        DB_LOCAL --> LST
        IMG_LOCAL --> LST
    end

    subgraph BRIDGE ["⚡ ΑΣΦΑΛΗΣ ΓΕΦΥΡΑ ΣΥΝΔΕΣΗΣ (Shop to Cloud API)"]
        API_PUSH["🛰️ Αποστολή Στοιχείων &amp; Ανέβασμα Φωτογραφιών (HTTPS)"]
        LST -->|Πάτημα Κουμπιού 'Ανέβασμα'| API_PUSH
    end

    subgraph CLOUD ["☁️ 2. CLOUD SERVER ΕΤΑΙΡΕΙΑΣ (VPS / Dedicated - 24/7 Uptime)"]
        DB_MASTER[("🌐 MASTER ΒΑΣΗ (autoexpo_parts.db)<br>• 17.730+ Ενεργές Αγγελίες")]
        IMG_CLOUD["📂 Cloud Storage (105 GB Φωτογραφίες - Fast CDN)"]
        XML_LIVE["📄 cargr_parts_feed.xml (Ζωντανό XML Feed 24/7)"]
        
        DASH_CARGR["💻 CARGR ROLE DASHBOARD<br>• Κεντρική εποπτεία 17.730 αγγελιών<br>• ✏️ Αλλαγές Τιμών, ✅ Πωλήθηκε, ⚡ Re-bump, 🛡️ Audit 20/20"]
        
        API_PUSH --> DB_MASTER
        API_PUSH --> IMG_CLOUD
        DB_MASTER --> XML_LIVE
        DB_MASTER --> DASH_CARGR
    end

    subgraph CARGR ["🚗 3. ΠΛΑΤΦΟΡΜΑ CAR.GR"]
        CAR_INGEST["🤖 Αυτόματος Συγχρονισμός Car.gr"]
        XML_LIVE -->|https://app.autoexpo.gr/feeds/cargr_parts_feed.xml| CAR_INGEST
    end
```

---

## 2. 📍 Πού Βρίσκεται το Κάθε Στοιχείο & Πώς Διαχωρίζονται οι 2 Βάσεις:

---

### 🏬 Α. ΣΤΟΝ ΤΟΠΙΚΟ SERVER ΤΟΥ ΜΑΓΑΖΙΟΥ (`server-magazi`):
Είναι ο υπολογιστής μέσα στο κατάστημα που εξυπηρετεί τη φυσική φωτογράφιση και απογραφή:
1. **Η Τοπική Βάση του Μαγαζιού (`autoparts_db.sqlite`):**  
   Κρατάει αποκλειστικά τα **νέα εισερχόμενα ανταλλακτικά** που φωτογραφίζονται στο ράφι.
2. **Οι Τοπικές Φωτογραφίες:**  
   Οι αρχικοί φάκελοι φωτογραφιών που ανεβάζει ο Manager από το κινητό του μέσω `/mobile`.
3. **Ο Ρόλος `manager`:**  
   Φωτογραφίζει με το κινητό και οργανώνει τα πακέτα φωτογραφιών.
4. **Ο Ρόλος `lister`:**  
   Βλέπει τις νέες φωτογραφίες στον τοπικό server, συμπληρώνει τους κωδικούς (OCR), το αυτοκίνητο, την τιμή και πατάει:  
   👉 **`[🚀 Ανέβασμα στο Car.gr]`**!

---

### ☁️ Β. ΣΤΟΝ CLOUD SERVER (VPS / Dedicated Cloud - 24/7):
Είναι ο κεντρικός εξωτερικός server στο internet που φιλοξενεί όλο το ζωντανό κατάστημα:
1. **Η Master Βάση Car.gr (`autoexpo_parts.db` - 213 MB):**  
   Περιέχει **και τις 17.730+ ενεργές αγγελίες** του καταστήματος με όλες τις λεπτομέρειες.
2. **Το Cloud Storage Φωτογραφιών (105.65 GB):**  
   Φιλοξενεί όλες τις 525.290 φωτογραφίες και τις σερβίρει με μέγιστη ταχύτητα μέσω HTTPS/CDN.
3. **Το Ζωντανό Car.gr XML Feed (`cargr_parts_feed.xml`):**  
   Σερβίρεται 24/7/365 απευθείας στο Car.gr (`https://app.autoexpo.gr/feeds/cargr_parts_feed.xml`).
4. **Ο Ρόλος `cargr` (XML Control Dashboard):**  
   Το κεντρικό dashboard στο cloud όπου γίνονται οι αλλαγές τιμών, τα μαρκαρίσματα πωλήσεων (`Πουλήθηκε`), τα re-bumps στην 1η σελίδα και οι έλεγχοι ακεραιότητας 20 σημείων!

---

## 3. 🚀 Η Ροή Ενός Νέου Ανταλλακτικού (Από το Ράφι στο Car.gr):

```
1. [ΜΑΓΑΖΙ] Manager φωτογραφίζει στο ράφι με κινητό (/mobile QR)
       │
       ▼
2. [ΜΑΓΑΖΙ] Lister ανοίγει την τοπική οθόνη, συμπληρώνει OEM & Τιμή
       │
       ▼
3. [ΜΑΓΑΖΙ] Lister πατάει "🚀 Ανέβασμα στο Car.gr"
       │
       ▼ (Ασφαλές HTTPS API Call στο Cloud)
4. [CLOUD]  Cloud Server παραλαμβάνει στοιχεία & φωτογραφίες
       │
       ├─► Αποθηκεύει στη Master Βάση (autoexpo_parts.db)
       ├─► Αποθηκεύει φωτογραφίες στο Cloud Storage (data/)
       ├─► Προσθέτει το <classified> στο cargr_parts_feed.xml
       │
       ▼
5. [CAR.GR] Το Car.gr διαβάζει το ανανεωμένο XML και η αγγελία είναι live!
```

---

## 4. 📅 Πλάνο Υλοποίησης (2 Ημέρες):

| Στάδιο | Αντικείμενο Εργασίας | Χρόνος |
| :--- | :--- | :---: |
| **Milestone 1** | **Cloud Server API & Master Database Handler:**<br>• Endpoints στο Cloud για υποδοχή νέων ανταλλακτικών & φωτογραφιών από το μαγαζί.<br>• Αυτόματη ανανέωση του `cargr_parts_feed.xml`. | **Ημέρα 1 (Πρωί)** |
| **Milestone 2** | **Shop Client Ingest Button:**<br>• Σύνδεση του κουμπιού «Ανέβασμα» στον τοπικό server του μαγαζιού με το Cloud API. | **Ημέρα 1 (Απόγευμα)** |
| **Milestone 3** | **Cargr Role Dashboard (Cloud UI):**<br>• Οθόνη διαχείρισης 17.730 αγγελιών, αλλαγές τιμών, κουμπιά «Πουλήθηκε», «Re-bump» & 20/20 Audit. | **Ημέρα 2 (Πρωί)** |
| **Milestone 4** | **Τελικός Έλεγχος & Cloud Deployment:**<br>• Δοκιμή ανέβασματος από το μαγαζί στο Cloud και επικύρωση XML Feed. | **Ημέρα 2 (Απόγευμα)** |
