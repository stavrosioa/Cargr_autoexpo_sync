import os
import sys

if sys.platform == "win32":
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
import json
import sqlite3
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_connection, DB_PATH, DATA_DIR, get_stats

PORT = 8088

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="el">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autoexpo Car.gr Parts Hub & Database Viewer</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #0b0f17;
            --bg-sidebar: #111827;
            --bg-card: #162032;
            --bg-card-hover: #1c2a42;
            --bg-input: #0d1522;
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --primary-glow: rgba(59, 130, 246, 0.25);
            --accent: #38bdf8;
            --price: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --border: #243247;
            --border-light: rgba(255,255,255,0.08);
            --radius-lg: 16px;
            --radius-md: 10px;
            --radius-sm: 6px;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-body);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .navbar {
            background: rgba(17, 24, 39, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 14px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-logo {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, var(--primary), #6366f1);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 20px;
            color: #fff;
            box-shadow: 0 0 20px var(--primary-glow);
        }
        .brand-title {
            font-size: 18px;
            font-weight: 800;
            letter-spacing: -0.3px;
            color: #fff;
        }
        .brand-sub {
            font-size: 12px;
            color: var(--text-muted);
        }

        .stats-pill {
            display: flex;
            align-items: center;
            gap: 18px;
            background: var(--bg-card);
            padding: 6px 16px;
            border-radius: 9999px;
            border: 1px solid var(--border);
            font-size: 13px;
        }
        .stat-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stat-val { font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }
        .stat-val.green { color: var(--price); }
        .stat-sep { width: 1px; height: 14px; background: var(--border); }

        .main-wrapper {
            max-width: 1540px;
            width: 100%;
            margin: 0 auto;
            padding: 24px;
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }

        .control-bar {
            background: var(--bg-sidebar);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 16px 20px;
            display: grid;
            grid-template-columns: 2.2fr 1fr 1fr 1fr auto;
            gap: 14px;
            align-items: center;
        }
        @media(max-width: 1100px) {
            .control-bar { grid-template-columns: 1fr 1fr; }
        }
        @media(max-width: 650px) {
            .control-bar { grid-template-columns: 1fr; }
        }

        .input-box {
            position: relative;
            display: flex;
            align-items: center;
        }
        .input-box input, .input-box select {
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 11px 14px;
            border-radius: var(--radius-md);
            font-size: 13.5px;
            font-family: inherit;
            outline: none;
            transition: all 0.2s ease;
        }
        .input-box input:focus, .input-box select:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
        }
        .btn-search {
            background: linear-gradient(135deg, var(--primary), var(--primary-hover));
            color: white;
            padding: 11px 22px;
            border-radius: var(--radius-md);
            border: none;
            font-weight: 700;
            font-size: 13.5px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px var(--primary-glow);
        }
        .btn-search:hover {
            transform: translateY(-1px);
            filter: brightness(1.1);
        }

        .results-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 13px;
            color: var(--text-muted);
            padding: 0 4px;
        }
        .results-count strong { color: var(--text-main); }

        .items-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
            gap: 20px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
        }
        .card:hover {
            transform: translateY(-4px);
            border-color: var(--accent);
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
        }

        .thumb-wrap {
            position: relative;
            width: 100%;
            height: 220px;
            background: #000;
            cursor: pointer;
            overflow: hidden;
        }
        .thumb-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }
        .card:hover .thumb-img {
            transform: scale(1.05);
        }
        .badge-photos {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(6px);
            border: 1px solid rgba(255,255,255,0.12);
            color: #38bdf8;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .badge-oem {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(245, 158, 11, 0.9);
            color: #000;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 800;
            padding: 3px 8px;
            border-radius: 6px;
            max-width: 85%;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .card-content {
            padding: 16px;
            display: flex;
            flex-direction: column;
            flex: 1;
            gap: 8px;
        }
        .card-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
        }
        .card-id {
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent);
            font-weight: 600;
        }
        .card-date {
            color: var(--text-dim);
        }
        .card-title {
            font-size: 14.5px;
            font-weight: 700;
            line-height: 1.35;
            color: #fff;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            min-height: 38px;
            cursor: pointer;
        }
        .card-title:hover {
            color: var(--accent);
        }
        .card-cat {
            font-size: 11.5px;
            color: var(--text-muted);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-compat {
            font-size: 11.5px;
            color: #93c5fd;
            background: rgba(59, 130, 246, 0.1);
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(59, 130, 246, 0.2);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .card-bottom {
            margin-top: auto;
            padding-top: 12px;
            border-top: 1px solid var(--border-light);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .price-tag {
            font-size: 18px;
            font-weight: 800;
            color: var(--price);
            font-family: 'JetBrains Mono', monospace;
        }
        .btn-view-details {
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-view-details:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: #fff;
        }

        .modal-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(8px);
            z-index: 2000;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .modal-overlay.active { display: flex; }
        .modal-card {
            background: var(--bg-sidebar);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            max-width: 1100px;
            width: 100%;
            max-height: 92vh;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            position: relative;
            box-shadow: 0 25px 60px rgba(0,0,0,0.6);
        }
        .modal-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            position: sticky;
            top: 0;
            background: var(--bg-sidebar);
            z-index: 10;
        }
        .modal-close {
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border);
            color: var(--text-muted);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 20px;
            transition: all 0.2s;
        }
        .modal-close:hover {
            background: #ef4444;
            color: #fff;
            border-color: #ef4444;
        }
        .modal-body {
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .gallery-title {
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #fff;
            margin-bottom: 12px;
        }
        .gallery-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 12px;
        }
        .gallery-item {
            position: relative;
            height: 160px;
            border-radius: var(--radius-md);
            overflow: hidden;
            background: #000;
            border: 1px solid var(--border);
            cursor: pointer;
        }
        .gallery-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }
        .gallery-item:hover img {
            transform: scale(1.08);
        }
        .gallery-badge {
            position: absolute;
            bottom: 6px;
            right: 6px;
            background: rgba(0,0,0,0.7);
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 4px;
            color: #fff;
        }

        .specs-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            background: var(--bg-card);
            padding: 18px;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }
        .spec-cell {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .spec-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-dim);
            font-weight: 700;
        }
        .spec-value {
            font-size: 13.5px;
            font-weight: 600;
            color: #fff;
        }
        .spec-value.mono {
            font-family: 'JetBrains Mono', monospace;
            color: #f59e0b;
        }

        .tags-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .tag-pill {
            background: rgba(56, 189, 248, 0.1);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
        }

        .desc-box {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px;
            font-size: 13.5px;
            line-height: 1.6;
            color: #cbd5e1;
            white-space: pre-line;
        }

        .compat-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            background: var(--bg-card);
            border-radius: var(--radius-md);
            overflow: hidden;
            border: 1px solid var(--border);
        }
        .compat-table th {
            background: rgba(255,255,255,0.04);
            padding: 10px 14px;
            text-align: left;
            font-weight: 700;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border);
        }
        .compat-table td {
            padding: 10px 14px;
            border-bottom: 1px solid var(--border-light);
            color: #fff;
        }
        .compat-table tr:last-child td { border-bottom: none; }

        .pagination-bar {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            padding: 20px 0;
        }
        .btn-page {
            background: var(--bg-card);
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: var(--radius-md);
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-page:hover:not(:disabled) {
            background: var(--primary);
            border-color: var(--primary);
            color: #fff;
        }
        .btn-page:disabled {
            opacity: 0.4;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="nav-brand">
            <div class="brand-logo">A</div>
            <div>
                <div class="brand-title">Autoexpo Car.gr Hub</div>
                <div class="brand-sub">Database Viewer & High-Res Asset Explorer</div>
            </div>
        </div>
        <div class="stats-pill">
            <div class="stat-item">
                <span>Αγγελίες:</span>
                <span class="stat-val" id="statListings">-</span>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item">
                <span>Φωτογραφίες (URLs):</span>
                <span class="stat-val green" id="statImages">-</span>
            </div>
            <div class="stat-sep"></div>
            <div class="stat-item">
                <span>Downloaded:</span>
                <span class="stat-val" id="statDownloaded">-</span>
            </div>
        </div>
    </nav>

    <div class="main-wrapper">
        <div class="control-bar">
            <div class="input-box">
                <input type="text" id="queryInput" placeholder="🔍 Αναζήτηση με Τίτλο, OEM Κωδικό, Μάρκα, Μοντέλο...">
            </div>
            <div class="input-box">
                <select id="makeSelect" onchange="applyFilters(1)">
                    <option value="">Όλες οι Μάρκες</option>
                </select>
            </div>
            <div class="input-box">
                <select id="categorySelect" onchange="applyFilters(1)">
                    <option value="">Όλες οι Κατηγορίες</option>
                </select>
            </div>
            <div class="input-box">
                <select id="sortSelect" onchange="applyFilters(1)">
                    <option value="id_desc">Νεότερες Πρώτα</option>
                    <option value="price_asc">Τιμή (Χαμηλή → Υψηλή)</option>
                    <option value="price_desc">Τιμή (Υψηλή → Χαμηλή)</option>
                    <option value="photos_desc">Περισσότερες Φωτογραφίες</option>
                </select>
            </div>
            <button class="btn-search" onclick="applyFilters(1)">
                <span>Αναζήτηση</span>
            </button>
        </div>

        <div class="results-info">
            <div class="results-count" id="resultsCount">Φόρτωση δεδομένων...</div>
            <div id="pageInfo"></div>
        </div>

        <div class="items-grid" id="listingsGrid"></div>

        <div class="pagination-bar" id="paginationBar"></div>
    </div>

    <!-- Modal for Detailed Inspection -->
    <div class="modal-overlay" id="detailModal" onclick="handleModalOverlayClick(event)">
        <div class="modal-card" id="modalCard">
            <div class="modal-header">
                <div>
                    <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 4px;">
                        <span class="card-id" id="mId">#54087039</span>
                        <span id="mDate" style="color: var(--text-dim); font-size: 12px;"></span>
                        <span id="mCondition" style="background: rgba(16, 185, 129, 0.15); color: var(--price); font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 700;"></span>
                    </div>
                    <h2 id="mTitle" style="font-size: 18px; color: #fff; line-height: 1.4;"></h2>
                </div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>

            <div class="modal-body">
                <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-card); padding: 14px 18px; border-radius: var(--radius-md); border: 1px solid var(--border);">
                    <div>
                        <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase; font-weight: 700;">Τιμή Πώλησης</div>
                        <div id="mPrice" style="font-size: 24px; font-weight: 800; color: var(--price); font-family: 'JetBrains Mono', monospace;"></div>
                    </div>
                    <a id="mCarGrUrl" href="#" target="_blank" class="btn-search" style="text-decoration: none;">
                        <span>Άνοιγμα στο Car.gr ↗</span>
                    </a>
                </div>

                <!-- Photos Gallery -->
                <div>
                    <div class="gallery-title">
                        <span>📸 Φωτογραφίες Αγγελίας (1024x768 HD)</span>
                        <span id="mPhotoCount" style="font-size: 12px; color: var(--accent);"></span>
                    </div>
                    <div class="gallery-grid" id="mGalleryGrid"></div>
                </div>

                <!-- Technical Specs -->
                <div class="specs-grid" id="mSpecsGrid"></div>

                <!-- Compatible Vehicles Table -->
                <div id="mCompatSection">
                    <div class="gallery-title">🚗 Συμβατά Αυτοκίνητα & Μοντέλα</div>
                    <table class="compat-table">
                        <thead>
                            <tr>
                                <th>Μάρκα</th>
                                <th>Μοντέλο</th>
                                <th>Έτη Κατασκευής</th>
                            </tr>
                        </thead>
                        <tbody id="mCompatBody"></tbody>
                    </table>
                </div>

                <!-- Keywords / Tags -->
                <div id="mTagsSection">
                    <div class="gallery-title">🏷️ Keywords & Search Tags</div>
                    <div class="tags-wrap" id="mTagsWrap"></div>
                </div>

                <!-- Full Description -->
                <div>
                    <div class="gallery-title">📝 Πλήρης Περιγραφή Αγγελίας</div>
                    <div class="desc-box" id="mDescBox"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentPage = 1;

        async function init() {
            await loadStats();
            await loadFilters();
            await applyFilters(1);
        }

        async function loadStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('statListings').innerText = Number(data.total_listings).toLocaleString('el-GR');
                document.getElementById('statImages').innerText = Number(data.total_images).toLocaleString('el-GR');
                document.getElementById('statDownloaded').innerText = Number(data.downloaded_images).toLocaleString('el-GR');
            } catch (e) {
                console.error(e);
            }
        }

        async function loadFilters() {
            try {
                const res = await fetch('/api/filter-options');
                const data = await res.json();

                const catSel = document.getElementById('categorySelect');
                data.categories.forEach(c => {
                    if (c) {
                        const opt = document.createElement('option');
                        opt.value = c;
                        opt.innerText = c;
                        catSel.appendChild(opt);
                    }
                });

                const makeSel = document.getElementById('makeSelect');
                data.makes.forEach(m => {
                    if (m) {
                        const opt = document.createElement('option');
                        opt.value = m;
                        opt.innerText = m;
                        makeSel.appendChild(opt);
                    }
                });
            } catch (e) {
                console.error(e);
            }
        }

        async function applyFilters(page = 1) {
            currentPage = page;
            const q = encodeURIComponent(document.getElementById('queryInput').value.trim());
            const cat = encodeURIComponent(document.getElementById('categorySelect').value);
            const make = encodeURIComponent(document.getElementById('makeSelect').value);
            const sort = document.getElementById('sortSelect').value;

            document.getElementById('resultsCount').innerText = 'Αναζήτηση...';

            try {
                const res = await fetch(`/api/listings?q=${q}&category=${cat}&make=${make}&sort=${sort}&page=${page}`);
                const data = await res.json();

                renderListings(data.items);
                renderPagination(data.total, data.page, data.per_page);
                
                document.getElementById('resultsCount').innerHTML = `Βρέθηκαν <strong>${data.total.toLocaleString('el-GR')}</strong> αγγελίες`;
            } catch (e) {
                console.error(e);
            }
        }

        function renderListings(items) {
            const grid = document.getElementById('listingsGrid');
            grid.innerHTML = '';

            if (!items || items.length === 0) {
                grid.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; background: var(--bg-card); border-radius: var(--radius-lg); border: 1px solid var(--border);">
                        <div style="font-size: 32px; margin-bottom: 10px;">🔍</div>
                        <h3 style="color: #fff; margin-bottom: 6px;">Δεν βρέθηκαν αποτελέσματα</h3>
                        <p style="color: var(--text-muted); font-size: 13.5px;">Δοκιμάστε διαφορετικές λέξεις αναζήτησης ή αφαιρέστε κάποια φίλτρα.</p>
                    </div>
                `;
                return;
            }

            items.forEach(it => {
                const card = document.createElement('div');
                card.className = 'card';
                const thumb = it.thumb_url || `https://static.car.gr/${it.id}_0_m.jpg`;
                const oemHtml = it.part_numbers ? `<div class="badge-oem">OEM: ${escapeHtml(it.part_numbers)}</div>` : '';
                const compatHtml = it.makes_models_summary ? `<div class="card-compat">🚗 ${escapeHtml(it.makes_models_summary)}</div>` : '';

                card.innerHTML = `
                    <div class="thumb-wrap" onclick="openDetailModal(${it.id})">
                        <img src="${thumb}" class="thumb-img" loading="lazy" onerror="this.src='https://via.placeholder.com/400x300?text=Car.gr+Photo'">
                        <div class="badge-photos">📸 ${it.photo_count || 0} φωτό</div>
                        ${oemHtml}
                    </div>
                    <div class="card-content">
                        <div class="card-top">
                            <span class="card-id">#${it.id}</span>
                            <span class="card-date">${it.created_at ? it.created_at.split(' ')[0] : ''}</span>
                        </div>
                        <div class="card-title" onclick="openDetailModal(${it.id})">${escapeHtml(it.title)}</div>
                        ${compatHtml}
                        <div class="card-cat">${escapeHtml(it.category || '')}</div>
                        <div class="card-bottom">
                            <div class="price-tag">${escapeHtml(it.price || 'Ρωτήστε')}</div>
                            <button class="btn-view-details" onclick="openDetailModal(${it.id})">Προβολή ➔</button>
                        </div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }

        function renderPagination(total, page, perPage) {
            const totalPages = Math.ceil(total / perPage) || 1;
            const bar = document.getElementById('paginationBar');
            bar.innerHTML = `
                <button class="btn-page" ${page <= 1 ? 'disabled' : ''} onclick="applyFilters(${page - 1})">◀ Προηγούμενη</button>
                <span style="font-size: 13.5px; color: var(--text-muted);">Σελίδα <strong style="color:#fff;">${page}</strong> από ${totalPages}</span>
                <button class="btn-page" ${page >= totalPages ? 'disabled' : ''} onclick="applyFilters(${page + 1})">Επόμενη ▶</button>
            `;
        }

        async function openDetailModal(id) {
            const modal = document.getElementById('detailModal');
            modal.classList.add('active');

            document.getElementById('mId').innerText = `#${id}`;
            document.getElementById('mTitle').innerText = 'Φόρτωση στοιχείων αγγελίας...';
            document.getElementById('mGalleryGrid').innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">Φόρτωση φωτογραφιών...</p>';

            try {
                const res = await fetch(`/api/listing/${id}`);
                const data = await res.json();

                document.getElementById('mTitle').innerText = data.title;
                document.getElementById('mDate').innerText = data.created_at ? `Δημοσιεύθηκε: ${data.created_at}` : '';
                document.getElementById('mCondition').innerText = data.condition || 'Μεταχειρισμένο';
                document.getElementById('mPrice').innerText = data.price || 'Ρωτήστε τιμή';
                document.getElementById('mCarGrUrl').href = data.url || `https://autoexpo.car.gr/parts/view/${id}/`;

                // Specs Grid
                const specsGrid = document.getElementById('mSpecsGrid');
                specsGrid.innerHTML = `
                    <div class="spec-cell">
                        <div class="spec-label">Εργοστασιακός Κωδικός (OEM)</div>
                        <div class="spec-value mono">${data.part_numbers || '-'}</div>
                    </div>
                    <div class="spec-cell">
                        <div class="spec-label">Κατηγορία</div>
                        <div class="spec-value">${data.category || '-'}</div>
                    </div>
                    <div class="spec-cell">
                        <div class="spec-label">Τοποθεσία / Διεύθυνση</div>
                        <div class="spec-value">${data.address_long || data.address || 'Άργος'}</div>
                    </div>
                    <div class="spec-cell">
                        <div class="spec-label">Τελευταία Τροποποίηση</div>
                        <div class="spec-value">${data.modified_at || '-'}</div>
                    </div>
                `;

                // Photos Gallery
                const gallery = document.getElementById('mGalleryGrid');
                gallery.innerHTML = '';
                document.getElementById('mPhotoCount').innerText = `(${data.images.length} φωτογραφίες)`;

                if (data.images.length === 0) {
                    gallery.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">Δεν υπάρχουν διαθέσιμες φωτογραφίες.</p>';
                } else {
                    data.images.forEach((img, idx) => {
                        const item = document.createElement('div');
                        item.className = 'gallery-item';
                        item.onclick = () => window.open(img.url_max_res, '_blank');
                        item.innerHTML = `
                            <img src="${img.url_max_res}" loading="lazy">
                            <div class="gallery-badge">#${idx + 1} • 1024x768</div>
                        `;
                        gallery.appendChild(item);
                    });
                }

                // Compatibility Table
                const compatSection = document.getElementById('mCompatSection');
                const compatBody = document.getElementById('mCompatBody');
                compatBody.innerHTML = '';
                if (data.compatible_vehicles && data.compatible_vehicles.length > 0) {
                    compatSection.style.display = 'block';
                    data.compatible_vehicles.forEach(v => {
                        const tr = document.createElement('tr');
                        const years = (v.year_from || v.year_to) ? `${v.year_from || ''} - ${v.year_to || ''}` : '-';
                        tr.innerHTML = `
                            <td><strong>${escapeHtml(v.make)}</strong></td>
                            <td>${escapeHtml(v.model)}</td>
                            <td style="font-family: 'JetBrains Mono', monospace; color: var(--accent);">${years}</td>
                        `;
                        compatBody.appendChild(tr);
                    });
                } else {
                    compatSection.style.display = 'none';
                }

                // Tags / Keywords
                const tagsSection = document.getElementById('mTagsSection');
                const tagsWrap = document.getElementById('mTagsWrap');
                tagsWrap.innerHTML = '';
                if (data.tags && data.tags.length > 0) {
                    tagsSection.style.display = 'block';
                    data.tags.forEach(t => {
                        const p = document.createElement('div');
                        p.className = 'tag-pill';
                        p.innerText = t;
                        tagsWrap.appendChild(p);
                    });
                } else {
                    tagsSection.style.display = 'none';
                }

                // Description Box
                document.getElementById('mDescBox').innerText = data.full_description || data.short_description || 'Δεν υπάρχει επιπλέον περιγραφή.';

            } catch (e) {
                console.error(e);
            }
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('active');
        }

        function handleModalOverlayClick(e) {
            if (e.target.id === 'detailModal') {
                closeModal();
            }
        }

        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });

        document.getElementById('queryInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') applyFilters(1);
        });

        function escapeHtml(str) {
            return (str || '').replace(/[&<>"']/g, m => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
            }[m]));
        }

        init();
    </script>
</body>
</html>
"""

class DBViewerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif path == "/api/stats":
            conn = get_connection()
            stats = get_stats(conn)
            conn.close()
            self._send_json(stats)
            return

        elif path == "/api/filter-options":
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM listings WHERE category IS NOT NULL AND category != '' ORDER BY category")
            categories = [r[0] for r in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT make FROM compatible_vehicles WHERE make IS NOT NULL AND make != '' ORDER BY make")
            makes = [r[0] for r in cursor.fetchall()]

            conn.close()
            self._send_json({
                "categories": categories,
                "makes": makes
            })
            return

        elif path == "/api/listings":
            q = query.get("q", [""])[0].strip()
            cat = query.get("category", [""])[0].strip()
            make = query.get("make", [""])[0].strip()
            sort = query.get("sort", ["id_desc"])[0]
            page = int(query.get("page", [1])[0])
            per_page = 24
            offset = (page - 1) * per_page

            conn = get_connection()
            cursor = conn.cursor()

            conditions = []
            params = []

            if q:
                conditions.append("""(
                    l.title LIKE ? OR 
                    l.descriptive_title LIKE ? OR 
                    l.part_numbers LIKE ? OR 
                    l.makes_models_summary LIKE ? OR 
                    l.keywords LIKE ? OR 
                    l.id = ?
                )""")
                wildcard = f"%{q}%"
                qid = int(q) if q.isdigit() else -1
                params.extend([wildcard, wildcard, wildcard, wildcard, wildcard, qid])

            if cat:
                conditions.append("l.category = ?")
                params.append(cat)

            if make:
                conditions.append("l.id IN (SELECT listing_id FROM compatible_vehicles WHERE make = ?)")
                params.append(make)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            order_by = "l.id DESC"
            if sort == "price_asc":
                order_by = "l.raw_price ASC"
            elif sort == "price_desc":
                order_by = "l.raw_price DESC"
            elif sort == "photos_desc":
                order_by = "l.photo_count DESC"

            cursor.execute(f"SELECT COUNT(*) FROM listings l {where_clause}", params)
            total = cursor.fetchone()[0]

            cursor.execute(f"""
            SELECT 
                l.id, l.title, l.price, l.raw_price, l.category, l.part_numbers, 
                l.makes_models_summary, l.photo_count, l.created_at, l.url,
                img.url_max_res as thumb_url
            FROM listings l
            LEFT JOIN listing_images img ON l.id = img.listing_id AND img.image_index = 0
            {where_clause}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?
            """, params + [per_page, offset])

            items = [dict(r) for r in cursor.fetchall()]
            conn.close()

            self._send_json({
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page
            })
            return

        elif path.startswith("/api/listing/"):
            parts = path.strip("/").split("/")
            lid = int(parts[2])

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM listings WHERE id = ?", (lid,))
            listing_row = cursor.fetchone()

            if not listing_row:
                conn.close()
                self.send_error(404, "Listing Not Found")
                return

            item = dict(listing_row)

            cursor.execute("SELECT id, image_index, url_max_res, local_path, is_downloaded FROM listing_images WHERE listing_id = ? ORDER BY image_index", (lid,))
            item["images"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT make, model, year_from, year_to FROM compatible_vehicles WHERE listing_id = ?", (lid,))
            item["compatible_vehicles"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT tag FROM listing_tags WHERE listing_id = ?", (lid,))
            item["tags"] = [r[0] for r in cursor.fetchall()]

            conn.close()
            self._send_json(item)
            return

        self.send_error(404, "Not Found")

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

def run_server(port=PORT):
    server = HTTPServer(("0.0.0.0", port), DBViewerHandler)
    print(f"\n🌐 Web Database Viewer is live at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(p)
