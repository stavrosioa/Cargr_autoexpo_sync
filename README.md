# Autoexpo Car.gr - Automated Scraper & Database Pipeline

Ολοκληρωμένο αυτοματοποιημένο σύστημα για τη συλλογή, αποθήκευση σε Database και λήψη φωτογραφιών μέγιστης ανάλυσης για όλες τις **17.730 αγγελίες** του καταστήματος Autoexpo στο Car.gr (`https://autoexpo.car.gr/parts/`).

---

## 🚀 Εντολές Χρήσης

Ενεργοποίηση περιβάλλοντος (Windows):
```powershell
.\venv\Scripts\activate
```

### 1. Έλεγχος Εγκατάστασης
```powershell
python check_env.py
```

### 2. Πλήρης Συλλογή Όλων των 17.730 Αγγελιών
Σαρώνει και τις 739 σελίδες και αποθηκεύει όλα τα δεδομένα και τα URLs των φωτογραφιών στη βάση SQLite:
```powershell
# Γρήγορη συλλογή καταλόγου (~2 λεπτά):
python main.py scrape

# Ή συλλογή με πλήρη ανάλυση OEM κωδικών & συμβατότητας οχημάτων:
python main.py scrape --deep
```

### 3. Έλεγχος & Συγχρονισμός Αγγελιών (Car.gr vs Database)
Συγκρίνει τις αγγελίες του καταστήματος στο Car.gr με τη βάση δεδομένων και εντοπίζει νέες ή διαγραμμένες αγγελίες:
```powershell
# Αναλυτική σύγκριση & εξαγωγή αναφοράς διαφορών σε CSV:
python main.py sync

# Αυτόματη συλλογή μόνο των νέων/ελλειπουσών αγγελιών στη βάση:
python main.py sync --fetch-missing

# Πλήρης συγχρονισμός (λήψη νέων + μαρκάρισμα πουλημένων ως ανενεργές):
python main.py sync --all
```

### 4. Έλεγχος Πληρότητας & Μοναδικότητας IDs
Επαληθεύει ότι έχουν συλλεχθεί και οι 17.730 μοναδικές αγγελίες χωρίς διπλότυπα:
```powershell
python main.py verify
```

### 5. Λήψη Όλων των Φωτογραφιών Μέγιστης Ανάλυσης (1024x768)
Κατεβάζει όλες τις φωτογραφίες ποιότητας HD στον τοπικό φάκελο `data/<ad_id>/`:
```powershell
python main.py download-images
```

### 5. Εκκίνηση Web Dashboard & Search Hub
Ανοίγει το γραφικό περιβάλλον στον browser για αναζήτηση με βάση μάρκα/μοντέλο, OEM κωδικό, κατηγορία, τιμή και προβολή γκαλερί:
```powershell
python main.py viewer
```
Ανοίγετε στον browser: **http://localhost:8088**

### 6. Εξαγωγή σε Excel (CSV) & JSON
```powershell
python main.py export
```
Δημιουργεί τα αρχεία:
- `database/autoexpo_parts.csv` (UTF-8 BOM για τέλεια εμφάνιση στο Excel)
- `database/autoexpo_parts.json`

### 7. Προβολή Στατιστικών
```powershell
python main.py stats
```
