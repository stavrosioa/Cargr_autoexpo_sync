#!/usr/bin/env python3
import sys
import os
import argparse

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

# Add scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

from database import init_db, get_connection, get_stats, DB_PATH, DATA_DIR, DB_DIR
from scraper import scrape_catalog, enrich_deep_details
from image_downloader import start_download
from exporter import export_to_csv, export_to_json
from viewer_app import run_server
from verify_all import verify_dataset
from sync_diff import run_sync_audit
from cargr_xml_generator import generate_cargr_xml, validate_cargr_xml

def main():
    parser = argparse.ArgumentParser(
        description="Autoexpo Car.gr Automated Scraper, Database & High-Res Image Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Δομή Φακέλων:
  • scripts/  -> Όλα τα εκτελέσιμα scripts (scraper, downloader, database, viewer, sync)
  • database/ -> Η βάση SQLite (database/autoexpo_parts.db) και τα εξαγόμενα αρχεία
  • data/     -> Ξεχωριστός φάκελος ανά αγγελία (data/<id>/) με λεπτομέρειες & φωτογραφίες

Παραδείγματα Χρήσης:
  python main.py scrape                     # Συλλογή όλων των 17.730 αγγελιών στη βάση
  python main.py sync                       # Έλεγχος ποιες αγγελίες υπάρχουν στο Car.gr vs στη Βάση (Diff Report)
  python main.py sync --fetch-missing       # Συγχρονισμός και αυτόματο κατέβασμα όσων λείπουν από τη βάση
  python main.py sync --all                 # Πλήρης συγχρονισμός (προσθήκη νέων + μαρκάρισμα πουλημένων)
  python main.py verify                     # Πλήρης έλεγχος και επιβεβαίωση πληρότητας
  python main.py download-images            # Λήψη όλων των high-res φωτογραφιών ανά αγγελία στο data/<id>/
  python main.py viewer                     # Εκκίνηση τοπικού Web Viewer (http://localhost:8088)
  python main.py export                     # Εξαγωγή σε CSV (Excel) & JSON στο database/
  python main.py stats                      # Προβολή στατιστικών βάσης δεδομένων
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Διαθέσιμες Εντολές")

    # Scrape command
    scrape_p = subparsers.add_parser("scrape", help="Συλλογή αγγελιών από το Car.gr στη βάση SQLite")
    scrape_p.add_argument("--pages", type=int, default=None, help="Μέγιστος αριθμός σελίδων (default: όλες οι 739 σελίδες)")
    scrape_p.add_argument("--workers", type=int, default=2, help="Αριθμός παράλληλων συνδέσεων (default: 2)")
    scrape_p.add_argument("--deep", action="store_true", help="Εκτέλεση και πλήρους βαθιάς ανάλυσης OEM & συμβατότητας")

    # Sync command
    sync_p = subparsers.add_parser("sync", help="Έλεγχος & σύγκριση αγγελιών Car.gr vs Βάσης Δεδομένων (Diff & Sync)")
    sync_p.add_argument("--fetch-missing", action="store_true", help="Αυτόματη συλλογή και αποθήκευση στη βάση όσων αγγελιών λείπουν")
    sync_p.add_argument("--mark-inactive", action="store_true", help="Μαρκάρισμα ως ανενεργές (is_active=0) όσων αγγελιών πουλήθηκαν/διαγράφηκαν")
    sync_p.add_argument("--all", action="store_true", help="Πλήρης συγχρονισμός (fetch missing + mark inactive)")
    sync_p.add_argument("--workers", type=int, default=2, help="Αριθμός παράλληλων συνδέσεων (default: 2)")

    # Verify command
    subparsers.add_parser("verify", help="Έλεγχος πληρότητας & επαλήθευση ότι έχουν συλλεχθεί και οι 17.730 μοναδικές αγγελίες")

    # Enrich command
    enrich_p = subparsers.add_parser("enrich", help="Αναλυτική εξαγωγή OEM κωδικών, συμβατότητας οχημάτων & keywords")
    enrich_p.add_argument("--limit", type=int, default=None, help="Μέγιστος αριθμός αγγελιών προς ανάλυση")
    enrich_p.add_argument("--workers", type=int, default=10, help="Αριθμός παράλληλων συνδέσεων (default: 10)")

    # Download images command
    img_p = subparsers.add_parser("download-images", help="Λήψη φωτογραφιών μέγιστης ανάλυσης στο data/<id>/")
    img_p.add_argument("--limit", type=int, default=None, help="Μέγιστος αριθμός φωτογραφιών για λήψη")
    img_p.add_argument("--concurrency", type=int, default=25, help="Αριθμός ταυτόχρονων downloads (default: 25)")
    img_p.add_argument("--output", type=str, default=DATA_DIR, help="Φάκελος προορισμού (default: data/)")

    # Export command
    exp_p = subparsers.add_parser("export", help="Εξαγωγή σε CSV και JSON στο database/")
    exp_p.add_argument("--format", choices=["all", "csv", "json"], default="all", help="Μορφή εξαγωγής")

    # Export XML command (Car.gr format)
    xml_p = subparsers.add_parser("export-xml", help="Δημιουργία Car.gr συμβατού XML Feed (Τοπικό Πείραμα / Dry-Run)")
    xml_p.add_argument("--limit", type=int, default=None, help="Μέγιστος αριθμός αγγελιών (default: όλες οι 17.730)")
    xml_p.add_argument("--max-photos", type=int, default=None, help="Όριο φωτογραφιών ανά αγγελία (π.χ. 6 για να αποφεύγονται οι κοινές φωτό μαγαζιού)")
    xml_p.add_argument("--output", type=str, default=None, help="Διαδρομή αρχείου XML (default: database/cargr_parts_feed.xml)")

    # Validate XML command
    val_p = subparsers.add_parser("validate-xml", help="Έλεγχος εγκυρότητας XML Feed σύμφωνα με τις προδιαγραφές Car.gr & W3")
    val_p.add_argument("--file", type=str, default=None, help="Διαδρομή αρχείου XML προς έλεγχο")

    # Viewer command
    view_p = subparsers.add_parser("viewer", help="Εκκίνηση Web Dashboard")
    view_p.add_argument("--port", type=int, default=8088, help="Θύρα web server (default: 8088)")

    # Stats command
    subparsers.add_parser("stats", help="Προβολή στατιστικών")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    init_db()

    if args.command == "scrape":
        scrape_catalog(max_pages=args.pages, workers=args.workers)
        if args.deep:
            enrich_deep_details(workers=args.workers)

    elif args.command == "sync":
        fetch_missing = args.fetch_missing or args.all
        mark_inactive = args.mark_inactive or args.all
        run_sync_audit(
            fetch_missing=fetch_missing,
            mark_inactive=mark_inactive,
            export_csv=True,
            workers=args.workers
        )

    elif args.command == "verify":
        verify_dataset()

    elif args.command == "enrich":
        enrich_deep_details(limit=args.limit, workers=args.workers)

    elif args.command == "download-images":
        start_download(limit=args.limit, concurrency=args.concurrency, output_dir=args.output)

    elif args.command == "export":
        if args.format in ("all", "csv"):
            export_to_csv()
        if args.format in ("all", "json"):
            export_to_json()

    elif args.command == "export-xml":
        generate_cargr_xml(
            output_path=args.output,
            limit=args.limit,
            max_photos_per_item=args.max_photos
        )

    elif args.command == "validate-xml":
        target = args.file or os.path.join(DB_DIR, "cargr_parts_feed.xml")
        validate_cargr_xml(target)

    elif args.command == "viewer":
        run_server(port=args.port)

    elif args.command == "stats":
        conn = get_connection()
        s = get_stats(conn)
        conn.close()
        print("\n📊 Στατιστικά Βάσης Δεδομένων:")
        print(f"  • Συνολικές αγγελίες: {s['total_listings']:,}")
        print(f"  • Μοναδικά IDs: {s['distinct_ids']:,}")
        print(f"  • Αγγελίες με βαθιά ανάλυση (OEM/Συμβατότητα): {s['deep_scraped']:,}")
        print(f"  • Συνολικές συσχετίσεις οχημάτων: {s['total_compat']:,}")
        print(f"  • Συνολικά Keywords / Tags: {s['total_tags']:,}")
        print(f"  • Συνολικές φωτογραφίες (URLs): {s['total_images']:,}")
        print(f"  • Αποθηκευμένες φωτογραφίες (downloaded): {s['downloaded_images']:,}")
        print(f"  • Ολοκληρωμένες σελίδες: {s['completed_pages']} / 739")
        print(f"  • Αρχείο βάσης: {DB_PATH}")
        print(f"  • Φάκελος αγγελιών: {DATA_DIR}\n")

if __name__ == "__main__":
    main()
