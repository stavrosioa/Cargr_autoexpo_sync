#!/usr/bin/env bash
echo "====================================================="
echo "🚗 Autoexpo Car.gr Pipeline - Setup & Installation"
echo "====================================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 δεν βρέθηκε! Παρακαλώ εγκαταστήστε την Python 3.9+."
    exit 1
fi

echo "📦 Δημιουργία Virtual Environment (venv)..."
python3 -m venv venv

echo "⚡ Ενεργοποίηση Virtual Environment..."
source venv/bin/activate

echo "⬇️ Εγκατάσταση Απαιτούμενων Βιβλιοθηκών (requirements.txt)..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "====================================================="
echo "✅ Η εγκατάσταση ολοκληρώθηκε επιτυχώς!"
echo ""
echo "Χρήσιμες Εντολές:"
echo "  1. Συλλογή αγγελιών:            python3 main.py scrape --deep"
echo "  2. Έλεγχος 17.730 αγγελιών:     python3 main.py verify"
echo "  3. Λήψη φωτογραφιών:           python3 main.py download-images"
echo "  4. Εκκίνηση Web Viewer:         python3 main.py viewer"
echo "  5. Εξαγωγή σε Excel/CSV & JSON: python3 main.py export"
echo "====================================================="
