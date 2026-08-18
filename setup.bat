@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo =====================================================
echo 🚗 Autoexpo Car.gr Pipeline - Setup & Installation
echo =====================================================

if not exist venv (
    echo 📦 Δημιουργία Virtual Environment (venv)...
    python -m venv venv
)

echo ⚡ Ενεργοποίηση Virtual Environment...
call venv\Scripts\activate

echo ⬇️ Εγκατάσταση Απαιτούμενων Βιβλιοθηκών (requirements.txt)...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo 🔍 Έλεγχος Περιβάλλοντος...
python check_env.py

echo.
echo =====================================================
echo ✅ Η εγκατάσταση είναι 100%% έτοιμη!
echo.
echo Χρήσιμες Εντολές (μέσα από το venv):
echo   1. Συλλογή όλων των αγγελιών:   python main.py scrape
echo   2. Συλλογή με OEM & μοντέλα:    python main.py scrape --deep
echo   3. Έλεγχος πληρότητας & IDs:    python main.py verify
echo   4. Λήψη όλων των φωτογραφιών:  python main.py download-images
echo   5. Εκκίνηση Web Dashboard:      python main.py viewer (http://localhost:8088)
echo   6. Εξαγωγή σε Excel & JSON:     python main.py export
echo   7. Προβολή στατιστικών:         python main.py stats
echo =====================================================
pause
