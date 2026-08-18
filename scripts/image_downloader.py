import sys
import os

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
import time
import asyncio
import aiohttp
import aiofiles
import sqlite3
from typing import Optional, List, Tuple
from tqdm.asyncio import tqdm

# Ensure scripts dir in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, DB_PATH, DATA_DIR

DEFAULT_DATA_DIR = DATA_DIR

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Referer": "https://autoexpo.car.gr/",
}

async def download_single_image(
    session: aiohttp.ClientSession,
    image_record: Tuple[int, int, int, str], # (id, listing_id, index, url_max_res)
    data_dir: str,
    semaphore: asyncio.Semaphore,
    pbar: tqdm,
    db_queue: asyncio.Queue
):
    img_id, listing_id, img_index, url = image_record
    
    # Each listing gets its dedicated folder in data/<listing_id>/
    listing_folder = os.path.join(data_dir, str(listing_id))
    ext = "jpg"
    local_filename = f"{img_index}.{ext}"
    local_filepath = os.path.join(listing_folder, local_filename)

    # Check if already on disk
    if os.path.exists(local_filepath) and os.path.getsize(local_filepath) > 1000:
        file_size = os.path.getsize(local_filepath)
        await db_queue.put((img_id, local_filepath, file_size))
        pbar.update(1)
        return

    async with semaphore:
        for attempt in range(4):
            try:
                async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        if len(content) > 500:
                            os.makedirs(listing_folder, exist_ok=True)
                            async with aiofiles.open(local_filepath, "wb") as f:
                                await f.write(content)
                            
                            file_size = len(content)
                            await db_queue.put((img_id, local_filepath, file_size))
                            pbar.update(1)
                            return
                            
                    elif resp.status == 404:
                        fallback_url = url.replace("_b.jpg", "_m.jpg")
                        if fallback_url != url:
                            async with session.get(fallback_url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as f_resp:
                                if f_resp.status == 200:
                                    content = await f_resp.read()
                                    os.makedirs(listing_folder, exist_ok=True)
                                    async with aiofiles.open(local_filepath, "wb") as f:
                                        await f.write(content)
                                    file_size = len(content)
                                    await db_queue.put((img_id, local_filepath, file_size))
                                    pbar.update(1)
                                    return
            except Exception:
                await asyncio.sleep(0.5 * (attempt + 1))

    pbar.update(1)

async def db_writer_task(db_queue: asyncio.Queue, db_path: str, stop_event: asyncio.Event):
    """Batch updates to SQLite."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    buffer = []

    while not stop_event.is_set() or not db_queue.empty():
        try:
            item = await asyncio.wait_for(db_queue.get(), timeout=1.0)
            buffer.append(item)
            db_queue.task_done()
        except asyncio.TimeoutError:
            pass

        if len(buffer) >= 100 or (buffer and db_queue.empty()):
            cursor.executemany("""
            UPDATE listing_images
            SET local_path = ?,
                file_size_bytes = ?,
                is_downloaded = 1,
                downloaded_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """, [(path, size, i_id) for i_id, path, size in buffer])
            conn.commit()
            buffer.clear()

    conn.close()

async def download_images_async(
    limit: Optional[int] = None,
    concurrency: int = 25,
    output_dir: str = DEFAULT_DATA_DIR,
    db_path: str = DB_PATH
):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT id, listing_id, image_index, url_max_res FROM listing_images WHERE is_downloaded = 0"
    if limit:
        query += f" LIMIT {limit}"

    cursor.execute(query)
    pending_records = cursor.fetchall()
    conn.close()

    total_pending = len(pending_records)
    print(f"\n🖼️ Φωτογραφίες προς λήψη (μέγιστη ανάλυση 1024x768): {total_pending:,}")
    print(f"📁 Φάκελος αποθήκευσης (ανά αγγελία): {output_dir}/<listing_id>/")
    print(f"⚡ Ταυτόχρονα downloads (concurrency): {concurrency}\n")

    if total_pending == 0:
        print("🎉 Όλες οι φωτογραφίες έχουν ήδη κατέβει!")
        return

    os.makedirs(output_dir, exist_ok=True)

    semaphore = asyncio.Semaphore(concurrency)
    db_queue = asyncio.Queue()
    stop_event = asyncio.Event()

    writer = asyncio.create_task(db_writer_task(db_queue, db_path, stop_event))
    pbar = tqdm(total=total_pending, desc="⬇️ Λήψη Φωτογραφιών", unit="img")

    conn_connector = aiohttp.TCPConnector(limit=concurrency + 10, ttl_dns_cache=300)
    async with aiohttp.ClientSession(connector=conn_connector) as session:
        tasks = [
            download_single_image(
                session,
                (r["id"], r["listing_id"], r["image_index"], r["url_max_res"]),
                output_dir,
                semaphore,
                pbar,
                db_queue
            )
            for r in pending_records
        ]
        await asyncio.gather(*tasks)

    pbar.close()
    stop_event.set()
    await writer

    # Summary
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(file_size_bytes) FROM listing_images WHERE is_downloaded = 1")
    count, total_bytes = cursor.fetchone()

    total_mb = (total_bytes or 0) / (1024 * 1024)
    total_gb = total_mb / 1024
    conn.close()

    print("\n" + "="*60)
    print(f"✅ Η λήψη των φωτογραφιών ολοκληρώθηκε!")
    print(f"📦 Σύνολο αποθηκευμένων φωτογραφιών: {count:,}")
    print(f"💾 Συνολικό μέγεθος στο δίσκο: {total_mb:.1f} MB ({total_gb:.2f} GB)")
    print("="*60 + "\n")

def start_download(limit: Optional[int] = None, concurrency: int = 25, output_dir: str = DEFAULT_DATA_DIR):
    asyncio.run(download_images_async(limit=limit, concurrency=concurrency, output_dir=output_dir))

if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else None
    start_download(limit=lim, concurrency=25)
