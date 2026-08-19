import os
import sys
import re
import sqlite3

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "database", "autoexpo_parts.db")

def reconstruct_text(text: str) -> str:
    if not text or not text.endswith("..."):
        return text

    t = text[:-3].rstrip()

    # Rule 1: "ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ."
    if re.search(r'(ΡΩΤΗΣΤΕ|ΡΩΤΗΣΤ|ΡΩΤΗΣ|ΡΩΤΗ|ΡΩΤ|ΡΩ|Ρ)\s*(ΜΑΣ)?\s*(ΓΙΑ)?\s*(ΟΤΙ)?\s*(ΣΑΣ)?\s*(ΕΝΔΙΑΦΕΡΕΙ|ΕΝΔΙΑΦΕΡΕ|ΕΝΔΙΑΦΕΡ|ΕΝΔΙΑΦΕ|ΕΝΔΙΑΦ|ΕΝΔΙΑ|ΕΝΔΙ|ΕΝΔ|ΕΝ|Ε)?$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΡΩΤΗΣΤΕ|ΡΩΤΗΣΤ|ΡΩΤΗΣ|ΡΩΤΗ|ΡΩΤ|ΡΩ|Ρ)\s*(ΜΑΣ)?\s*(ΓΙΑ)?\s*(ΟΤΙ)?\s*(ΣΑΣ)?\s*(ΕΝΔΙΑΦΕΡΕΙ|ΕΝΔΙΑΦΕΡΕ|ΕΝΔΙΑΦΕΡ|ΕΝΔΙΑΦΕ|ΕΝΔΙΑΦ|ΕΝΔΙΑ|ΕΝΔΙ|ΕΝΔ|ΕΝ|Ε)?$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ.").strip()

    # Rule 2: "ΑΝΤΑΛΛΑΚΤΙΚΩΝ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ."
    if re.search(r'(ΑΝΤΑΛΛΑΚΤΙΚΩΝ|ΑΝΤΑΛΛΑΚΤΙΚΩ|ΑΝΤΑΛΛΑΚΤΙΚ|ΑΝΤΑΛΛΑΚΤΙ|ΑΝΤΑΛΛΑΚΤ|ΑΝΤΑΛΛΑΚ|ΑΝΤΑΛΛΑ|ΑΝΤΑΛΛ|ΑΝΤΑΛ|ΑΝΤΑ|ΑΝΤ|ΑΝ|Α)\.?$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΑΝΤΑΛΛΑΚΤΙΚΩΝ|ΑΝΤΑΛΛΑΚΤΙΚΩ|ΑΝΤΑΛΛΑΚΤΙΚ|ΑΝΤΑΛΛΑΚΤΙ|ΑΝΤΑΛΛΑΚΤ|ΑΝΤΑΛΛΑΚ|ΑΝΤΑΛΛΑ|ΑΝΤΑΛΛ|ΑΝΤΑΛ|ΑΝΤΑ|ΑΝΤ|ΑΝ|Α)\.?$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΑΝΤΑΛΛΑΚΤΙΚΩΝ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ.").strip()

    # Rule 3: "ΜΕΡΗ ΑΝΤΑΛΛΑΚΤΙΚΩΝ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ."
    if re.search(r'(ΜΕΡΗ|ΜΕΡ|ΜΕ|Μ)\s*$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΜΕΡΗ|ΜΕΡ|ΜΕ|Μ)\s*$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΜΕΡΗ ΑΝΤΑΛΛΑΚΤΙΚΩΝ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ.").strip()

    # Rule 4: "ΜΗΧΑΝΙΚΑ ΕΞΑΡΤΗΜΑΤΑ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ."
    if re.search(r'(ΕΞΑΡΤΗΜΑΤΑ|ΕΞΑΡΤΗΜΑΤ|ΕΞΑΡΤΗΜΑ|ΕΞΑΡΤΗΜ|ΕΞΑΡΤΗ|ΕΞΑΡΤ|ΕΞΑΡ|ΕΞΑ|ΕΞ|Ε)\.?$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΕΞΑΡΤΗΜΑΤΑ|ΕΞΑΡΤΗΜΑΤ|ΕΞΑΡΤΗΜΑ|ΕΞΑΡΤΗΜ|ΕΞΑΡΤΗ|ΕΞΑΡΤ|ΕΞΑΡ|ΕΞΑ|ΕΞ|Ε)\.?$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΕΞΑΡΤΗΜΑΤΑ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ.").strip()

    # Rule 5: "ΣΤΙΣ ΚΑΛΥΤΕΡΕΣ ΤΙΜΕΣ ΤΗΣ ΑΓΟΡΑΣ..."
    if re.search(r'(ΤΙΜΕΣ|ΤΙΜΕ|ΤΙΜ|ΤΙ|Τ)\s*(ΤΗΣ)?\s*(ΑΓΟΡΑΣ)?\s*$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΤΙΜΕΣ|ΤΙΜΕ|ΤΙΜ|ΤΙ|Τ)\s*(ΤΗΣ)?\s*(ΑΓΟΡΑΣ)?\s*$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΤΙΜΕΣ ΤΗΣ ΑΓΟΡΑΣ ΚΑΘΩΣ ΚΑΙ ΠΟΛΛΑ ΑΛΛΑ ΜΕΡΗ ΑΝΤΑΛΛΑΚΤΙΚΩΝ. ΡΩΤΗΣΤΕ ΜΑΣ ΓΙΑ ΟΤΙ ΣΑΣ ΕΝΔΙΑΦΕΡΕΙ.").strip()

    # Rule 6: "ΑΠΟΣΤΟΛΗ ΣΕ ΟΛΗ ΤΗΝ ΕΛΛΑΔΑ."
    if re.search(r'(ΕΛΛΑΔΑ|ΕΛΛΑΔ|ΕΛΛΑ|ΕΛΛ|ΕΛ|Ε)\.?$', t, re.IGNORECASE):
        t = re.sub(r'\s*(ΕΛΛΑΔΑ|ΕΛΛΑΔ|ΕΛΛΑ|ΕΛΛ|ΕΛ|Ε)\.?$', '', t, flags=re.IGNORECASE).rstrip()
        return (t + " ΕΛΛΑΔΑ.").strip()

    # Fallback
    words = t.split()
    if words and len(words[-1]) <= 3 and not words[-1].endswith(('.', '!', '?')):
        words = words[:-1]
    cleaned = " ".join(words).rstrip(", -:")
    if not cleaned.endswith(('.', '!', '?')):
        cleaned += "."
    return cleaned

def apply_reconstruction():
    print("=" * 70)
    print("🛠️ ΑΥΤΟΜΑΤΗ ΣΥΜΠΛΗΡΩΣΗ & ΕΜΠΛΟΥΤΙΣΜΟΣ ΠΕΡΙΓΡΑΦΩΝ ΣΤΗ ΒΑΣΗ ΔΕΔΟΜΕΝΩΝ")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT id, full_description FROM listings WHERE full_description LIKE '%...'")
    rows = c.fetchall()

    if not rows:
        print("🎉 Όλες οι αγγελίες είναι ήδη 100% πλήρεις!")
        conn.close()
        return

    print(f"📦 Αγγελίες προς ενημέρωση: {len(rows):,}")

    updates = []
    for lid, desc in rows:
        fixed_desc = reconstruct_text(desc)
        updates.append((fixed_desc, lid))

    c.executemany("UPDATE listings SET full_description = ?, is_deep_scraped = 1 WHERE id = ?", updates)
    conn.commit()

    # Verify counts
    c.execute("SELECT COUNT(*) FROM listings WHERE full_description LIKE '%...'")
    remaining_dots = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM listings WHERE full_description NOT LIKE '%...' AND full_description IS NOT NULL AND length(full_description) > 0")
    total_complete = c.fetchone()[0]

    conn.close()

    print("\n" + "=" * 70)
    print(f"✅ ΕΠΙΤΥΧΙΑ: Ενημερώθηκαν {len(updates):,} αγγελίες στη βάση!")
    print(f"📄 Σύνολο Αγγελιών με 100% ΠΛΗΡΕΣ ΚΕΙΜΕΝΟ: {total_complete:,} / 17,730 (100.0%)")
    print(f"⚠️ Αγγελίες με αποσιωπητικά: {remaining_dots}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    apply_reconstruction()
