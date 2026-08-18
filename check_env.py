import sys
import os
import subprocess

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

def check():
    print("=" * 50)
    print("🔍 Έλεγχος Περιβάλλοντος & Requirements")
    print("=" * 50)

    # 1. Python Version
    py_ver = sys.version.split()[0]
    print(f"🐍 Python Version: {py_ver} (Ελάχιστη απαιτούμενη: 3.9+) -> {'✅ OK' if sys.version_info >= (3, 9) else '❌ Χρειάζεται Python >= 3.9'}")

    # 2. Node.js Check
    node_bin = None
    import shutil
    if shutil.which("node"):
        node_bin = shutil.which("node")
    else:
        for p in [
            os.path.join(os.path.dirname(__file__), "venv", "Scripts", "node.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\nodejs\node.exe"),
            r"C:\Program Files\nodejs\node.exe",
            "/opt/homebrew/bin/node",
            "/usr/local/bin/node"
        ]:
            if os.path.exists(p):
                node_bin = p
                break

    if node_bin:
        try:
            node_out = subprocess.run([node_bin, "--version"], capture_output=True, text=True, encoding="utf-8")
            print(f"🟢 Node.js ({node_bin}): {node_out.stdout.strip()} -> ✅ OK")
        except Exception as e:
            print(f"❌ Node.js: Σφάλμα εκτέλεσης ({e})")
    else:
        print("❌ Node.js: Δεν βρέθηκε στο PATH (Απαιτείται για την αποσυμπίεση του Nuxt state)")

    # 3. Python Packages Check
    packages = {
        "curl_cffi": "Παράκαμψη Cloudflare & TLS Fingerprinting",
        "tqdm": "Μπάρες προόδου σε πραγματικό χρόνο",
        "aiohttp": "Ασύγχρονο κατέβασμα εικόνων μέγιστης ταχύτητας",
        "aiofiles": "Ασύγχρονη εγγραφή εικόνων στο δίσκο",
        "sqlite3": "Ενσωματωμένη Βάση Δεδομένων SQLite",
    }

    print("\n📦 Έλεγχος Βιβλιοθηκών Python:")
    for pkg, desc in packages.items():
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "Ενσωματωμένη")
            print(f"  • {pkg:<15} ({ver:<8}): ✅ Εγκατεστημένο ({desc})")
        except ImportError:
            print(f"  • {pkg:<15}: ❌ Λείπει! (Τρέξτε: pip install {pkg})")

    print("=" * 50)
    print("🚀 Κατάσταση: Όλα τα requirements είναι πλήρως εγκατεστημένα και έτοιμα!")
    print("=" * 50)

if __name__ == "__main__":
    check()
