import copy
import os
import hashlib
from urllib.parse import quote
import fitz
import streamlit as st
from engine import (
    parse_page_input,
    add_duplex_pairs,
    split_pdf_by_pages,
    process_and_split_pdf,
    get_pdf_page_count,
    format_rupiah as rp,
)
from settings import DEFAULT, setup, read, save, calculate, validate, connect

st.set_page_config(
    page_title='LitnusPro • Studio Cetak v1.2.5',
    page_icon='📚',
    layout='wide',
    initial_sidebar_state='collapsed',
)

# ==========================================
# KOLEKSI IKON SVG PROPORSIONAL (2X FONT)
# ==========================================
MENU = {
    'Kalkulator Cepat': (
        'Jumlah halaman saja',
        '<rect x="3" y="3" width="7" height="7" rx="1.8"/><rect x="14" y="3" width="7" height="7" rx="1.8"/><rect x="3" y="14" width="7" height="7" rx="1.8"/><rect x="14" y="14" width="7" height="7" rx="1.8"/>',
    ),
    'Deteksi Warna PDF': (
        'Analisis warna otomatis',
        '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    ),
    'Pilah Halaman PDF': (
        'Pilih halaman manual',
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="16" y2="17"/>',
    ),
    'Admin Tarif': (
        None,
        '<rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    ),
}


@st.cache_data(show_spinner=False)
def icon_svg(path, color='#0d8480', size=30):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" '
        f'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'
    )


@st.cache_data(show_spinner=False)
def icon_data_uri(path, color='#0d8480', size=30):
    return quote(icon_svg(path, color, size), safe='')


# ==========================================
# ENGINE INTERNAL: AUTO-DETECT KOMPLEKSITAS TONER FULL COLOUR
# ==========================================
@st.cache_data(show_spinner='Menganalisis proporsi cakupan blok warna di seluruh halaman...')
def analyze_full_color_toner_pdf(file_bytes, total_p):
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    page_toner_pcts = {}

    for page_num in range(total_p):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=54, colorspace=fitz.csRGB)
        samples = pix.samples
        n = pix.n
        step = n * 4
        sample_count = 0
        color_coverage_sum = 0.0

        for i in range(0, len(samples) - n + 1, step):
            r = samples[i]
            g = samples[i + 1]
            b = samples[i + 2]
            sample_count += 1

            if r >= 242 and g >= 242 and b >= 242:
                continue

            max_c = max(r, g, b)
            min_c = min(r, g, b)
            chroma = max_c - min_c

            if chroma >= 12:
                ink_intensity = (255 - min_c) / 255.0
                color_coverage_sum += min(1.0, 0.82 + (ink_intensity * 0.25))
            else:
                darkness = (255 - max_c) / 255.0
                if darkness > 0.65:
                    color_coverage_sum += darkness * 0.15

        pct = (color_coverage_sum / sample_count * 100.0) if sample_count else 0.0
        page_toner_pcts[page_num + 1] = round(min(100.0, max(0.0, pct)), 1)

    doc.close()
    all_pages = list(range(1, total_p + 1))
    return all_pages, [], file_bytes, None, page_toner_pcts


def calculate_with_toner_complexity(
    d,
    size,
    paper,
    mode,
    binding,
    qty,
    color,
    bw,
    override=None,
    full_color_complexity_mode=False,
    page_toner_pcts=None,
):
    base_res = calculate(d, size, paper, mode, binding, qty, color, bw, override)
    base_res.setdefault('avg_toner_pct', 0.0)
    base_res.setdefault('toner_savings_unit', 0)
    base_res.setdefault('toner_savings_total', 0)
    base_res.setdefault('avg_page_rate', base_res.get('color_rate', 0))

    total_pages = color + bw
    if not full_color_complexity_mode or not page_toner_pcts or total_pages <= 0:
        return base_res

    cr = base_res['color_rate']
    br = base_res['bw_rate']
    f = base_res['finishing']

    toner_margin_100 = max(0, cr - br)
    total_content_cost = 0.0
    toner_sum = 0.0

    for pno in range(1, total_pages + 1):
        pct = float(page_toner_pcts.get(pno, 0.0))
        pct = max(0.0, min(100.0, pct))
        toner_sum += pct
        page_cost = br + (pct / 100.0) * toner_margin_100
        total_content_cost += page_cost

    content_cost_per_book = int(round(total_content_cost))
    avg_toner_pct = round(toner_sum / total_pages, 2)
    avg_page_rate = int(round(content_cost_per_book / total_pages))

    full_block_content_per_book = total_pages * cr
    toner_savings_unit = max(0, full_block_content_per_book - content_cost_per_book)

    unit = content_cost_per_book + f
    total_cost = unit * qty
    dp_cost = int(total_cost * d['dp'] / 100)

    base_res.update(
        unit=unit,
        total=total_cost,
        dp=dp_cost,
        avg_toner_pct=avg_toner_pct,
        toner_savings_unit=toner_savings_unit,
        toner_savings_total=toner_savings_unit * qty,
        avg_page_rate=avg_page_rate,
    )
    return base_res


# ==========================================
# CSS TEMA FLOATING CANVAS (RESPONSIF, SCROLLBAR AMAN, TOMBOL SESI MENTOK BAWAH)
# ==========================================
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');

:root {
    --canvas-height: 92vh;
    --canvas-margin: 4vh;
    --canvas-inset: 20px;
    --litnus-green-start: #0b6e6d;
    --litnus-green-end: #178d89;
    --litnus-green-gradient: linear-gradient(95deg, var(--litnus-green-start), var(--litnus-green-end));
}
@supports (height: 100dvh) {
    :root {
        --canvas-height: 92dvh;
        --canvas-margin: 4dvh;
    }
}

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif !important;
    color: #142829;
}

html, body, [data-testid="stAppViewContainer"] {
    overflow: hidden !important;
    height: 100vh !important;
    height: 100dvh !important;
}
[data-testid="stMain"], .main {
    height: 100% !important;
    min-height: 0 !important;
    overflow: hidden !important;
}

header[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {
    display: none !important;
}

.stApp {
    background:
        radial-gradient(circle at 92% 45%, rgba(208, 198, 240, 0.65) 0%, transparent 45%),
        radial-gradient(circle at 15% 85%, rgba(164, 206, 202, 0.7) 0%, transparent 55%),
        linear-gradient(135deg, #b7d4d0 0%, #c8e0dc 50%, #bfd6d8 100%) !important;
    background-attachment: fixed !important;
}

.block-container {
    max-width: 1360px !important;
    width: 95vw !important;
    height: var(--canvas-height) !important;
    margin: var(--canvas-margin) auto !important;
    padding: 0 !important;
    display: block !important;
    background: linear-gradient(125deg, rgba(232, 244, 242, 0.96) 0%, rgba(220, 238, 236, 0.93) 65%, rgba(232, 230, 245, 0.93) 100%) !important;
    border: 2.5px solid rgba(255, 255, 255, 0.88) !important;
    border-radius: 34px !important;
    box-shadow:
        0 28px 60px rgba(18, 52, 56, 0.14),
        0 10px 22px rgba(18, 52, 56, 0.06),
        inset 0 1px 2px rgba(255, 255, 255, 0.95) !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

/* The frame owns the height; only its inset workspace scrolls on desktop. */
.block-container > [data-testid="stVerticalBlock"],
.block-container > [data-testid="stVerticalBlockBorderWrapper"],
.block-container > [data-testid="stVerticalBlockBorderWrapper"] > div,
.block-container > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"],
.st-key-canvas_shell,
.st-key-canvas_shell > div,
.st-key-canvas_shell > div > [data-testid="stVerticalBlock"],
.st-key-canvas_shell [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-canvas_sidebar) {
    height: 100% !important;
    min-height: 0 !important;
    gap: 0 !important;
}
.st-key-canvas_shell [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-canvas_sidebar) {
    flex-wrap: nowrap !important;
    align-items: stretch !important;
}
.block-container [data-testid="stLayoutWrapper"]:has(.st-key-canvas_shell),
.st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_sidebar),
.st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_main) {
    height: 100% !important;
    min-height: 0 !important;
    flex: 1 1 0% !important;
}
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar) {
    flex: 0 0 300px !important;
    width: 300px !important;
}
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main) {
    flex: 1 1 0% !important;
    padding: var(--canvas-inset) 16px var(--canvas-inset) 0 !important;
    box-sizing: border-box !important;
}
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar),
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main),
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar) > div,
.st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main) > div {
    height: 100% !important;
    min-height: 0 !important;
}
.st-key-canvas_shell [data-testid="stColumn"],
.st-key-canvas_shell [data-testid="stVerticalBlock"],
.st-key-canvas_shell [data-testid="stLayoutWrapper"],
.st-key-canvas_shell [data-testid="stElementContainer"],
.st-key-canvas_shell [data-testid="stMarkdownContainer"] {
    min-width: 0 !important;
    box-sizing: border-box !important;
}
.st-key-canvas_main [data-testid="stElementContainer"] {
    max-width: 100%;
}

.st-key-canvas_sidebar {
    padding: 2.1rem 1.4rem 1.6rem 1.85rem !important;
    border-right: 1.5px solid rgba(255, 255, 255, 0.65);
    height: 100% !important;
    min-height: 0 !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    box-sizing: border-box !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}
.st-key-canvas_sidebar[data-testid="stVerticalBlockBorderWrapper"] > div,
.st-key-canvas_sidebar[data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: space-between !important;
}

.st-key-canvas_main {
    padding: 1.2rem 1.4rem 2rem 1.6rem !important;
    margin: 0 !important;
    width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    max-height: 100% !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-gutter: stable;
    overscroll-behavior-y: contain;
    box-sizing: border-box !important;
}
.st-key-canvas_main > *, .st-key-canvas_sidebar > * {
    flex-shrink: 0;
}

/* Standard colors are the fallback for browsers without WebKit scrollbars. */
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main) {
    scrollbar-color: var(--litnus-green-start) rgba(13, 122, 118, 0.08) !important;
    scrollbar-width: thin !important;
}
@supports selector(::-webkit-scrollbar) {
    /* Non-auto standard properties override gradient thumbs in Chrome/Edge. */
    :is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main) {
        scrollbar-color: auto !important;
        scrollbar-width: auto !important;
    }
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar {
    width: 10px !important;
    height: 10px !important;
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar-track {
    background: rgba(13, 122, 118, 0.08) !important;
    border-radius: 99px !important;
    margin-block: 4px !important;
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--litnus-green-start), var(--litnus-green-end)) !important;
    border-radius: 99px !important;
    border: 2px solid transparent !important;
    background-clip: padding-box !important;
    min-height: 44px !important;
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #085554 0%, #0d7a76 100%) !important;
    background-clip: padding-box !important;
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar-button {
    display: none !important;
    width: 0 !important;
    height: 0 !important;
}
:is(.st-key-canvas_main, .st-key-canvas_sidebar, .toner-scroll-box, [data-testid="stMain"], .main)::-webkit-scrollbar-corner {
    background: transparent !important;
}

.brand-logo {
    font-size: 2.05rem;
    font-weight: 800;
    color: #142829;
    letter-spacing: -0.03em;
    padding: 0.1rem 0.5rem 1.5rem 0.5rem;
    line-height: 1.1;
}
.brand-logo span {
    font-weight: 800;
    background: linear-gradient(95deg, #0b6e6d 0%, #178d89 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    color: #0d7a76;
}

.st-key-nav_menu button, .st-key-nav_admin button, .st-key-nav_session button {
    min-height: 52px !important;
    width: 100% !important;
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    text-align: left !important;
    padding: 0.55rem 1.05rem !important;
    border-radius: 16px !important;
    border: none !important;
    background: transparent !important;
    color: #0d7a76 !important;
    font-size: 0.94rem !important;
    font-weight: 600 !important;
    box-shadow: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    margin-bottom: 0.35rem !important;
    box-sizing: border-box !important;
}

.st-key-nav_menu button > div, .st-key-nav_admin button > div, .st-key-nav_session button > div {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    width: 100% !important;
    gap: 10px !important;
}

.st-key-nav_menu button p, .st-key-nav_admin button p, .st-key-nav_session button p {
    font-size: 0.93rem !important;
    font-weight: 600 !important;
    margin: 0 !important;
    text-align: left !important;
    display: flex !important;
    align-items: center !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
}

.st-key-nav_menu button img, .st-key-nav_admin button img, .st-key-nav_session button img {
    width: 28px !important;
    height: 28px !important;
    margin-right: 10px !important;
    vertical-align: middle !important;
    flex-shrink: 0 !important;
}

.st-key-nav_menu button:hover, .st-key-nav_admin button:hover, .st-key-nav_session button:hover {
    background: rgba(255, 255, 255, 0.55) !important;
    color: #065a57 !important;
}

.st-key-nav_menu button[kind="primary"], .st-key-nav_admin button[kind="primary"], .st-key-nav_session button[kind="primary"] {
    background: var(--litnus-green-gradient) !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 10px 22px -6px rgba(11, 110, 109, 0.42) !important;
}

.st-key-nav_menu button[kind="primary"] p, .st-key-nav_admin button[kind="primary"] p, .st-key-nav_session button[kind="primary"] p {
    color: #ffffff !important;
    font-weight: 600 !important;
}

.st-key-nav_admin {
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid rgba(13, 122, 118, 0.15);
}

/* Tombol Keluar / Ganti Sesi: Diikat dalam Flex Flow Sidebar agar Mentok Bawah & Tidak Terpotong Kanan */
.st-key-nav_session {
    margin-top: auto !important;
    padding-top: 0.85rem !important;
    border-top: 1px solid rgba(13, 122, 118, 0.16);
    width: 100% !important;
    box-sizing: border-box !important;
}
.st-key-nav_session button {
    background: rgba(255, 255, 255, 0.68) !important;
    border: 1.5px solid rgba(13, 122, 118, 0.24) !important;
    margin-bottom: 0 !important;
    width: 100% !important;
}

/* Topbar Responsif (Satu Baris Horizontal) */
.topbar-wrap {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: center !important;
    margin-bottom: 1.25rem !important;
    gap: 16px !important;
    width: 100% !important;
    flex-wrap: wrap;
}
.topbar-wrap > div {
    min-width: 0;
    max-width: 100%;
}
.welcome-text {
    font-size: 0.94rem;
    font-weight: 500;
    color: #0e7c77;
    margin-bottom: 0.1rem;
    overflow-wrap: anywhere;
}
.page-main-title {
    font-size: 2.1rem;
    font-weight: 700;
    color: #152223;
    letter-spacing: -0.03em;
    line-height: 1.15;
    margin: 0;
    overflow-wrap: anywhere;
}
.user-profile-bar {
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    min-width: 0;
}
.top-icon-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0c7470;
    opacity: 0.9;
}
.user-chip {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(255, 255, 255, 0.55);
    padding: 4px 12px 4px 5px;
    border-radius: 99px;
    border: 1px solid rgba(255, 255, 255, 0.85);
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
}
.user-avatar {
    width: 34px;
    height: 34px;
    flex-shrink: 0;
    border-radius: 50%;
    background: linear-gradient(135deg, #0b6e6d, #199c96);
    color: #ffffff;
    font-weight: 600;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #ffffff;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.08);
}
.user-name {
    font-size: 0.85rem;
    font-weight: 600;
    color: #162a2b;
    min-width: 0;
    overflow-wrap: anywhere;
}

/* Glass Containers & Input Styles */
.st-key-card_naskah,
.st-key-card_spek,
.st-key-card_total,
.st-key-card_admin_login,
.st-key-card_admin_info,
.st-key-card_admin_panel,
.st-key-card_admin_tiers,
.st-key-card_admin_save,
.st-key-card_session_google,
.st-key-card_session_guest {
    background: rgba(238, 247, 245, 0.72) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.82) !important;
    border-radius: 24px !important;
    padding: 1.35rem 1.6rem !important;
    box-shadow: 0 12px 26px -8px rgba(17, 60, 58, 0.06) !important;
    margin-bottom: 1.15rem !important;
    min-width: 0 !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
    container-type: inline-size;
}

.card-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.85rem;
    flex-wrap: wrap;
    gap: 0.4rem 0.75rem;
}
.card-header-row > * {
    min-width: 0;
    overflow-wrap: anywhere;
}
.card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #182b2c;
    margin: 0;
}
.card-action-link {
    font-size: 0.8rem;
    font-weight: 600;
    color: #0e7c77;
}

div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
    background-color: rgba(255, 255, 255, 0.84) !important;
    border: 1px solid rgba(255, 255, 255, 0.95) !important;
    border-radius: 14px !important;
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
    border-color: #0e7c77 !important;
    background-color: #ffffff !important;
}
[data-testid="stFileUploaderDropzone"] {
    background-color: rgba(255, 255, 255, 0.68) !important;
    border: 1.5px dashed rgba(14, 124, 119, 0.38) !important;
    border-radius: 16px !important;
}

.st-key-accent_title div[data-baseweb="input"] {
    background: linear-gradient(95deg, rgba(13, 122, 118, 0.12) 0%, rgba(23, 141, 137, 0.08) 100%) !important;
    border: 2px solid #0d7a76 !important;
    border-radius: 14px !important;
    box-shadow: 0 4px 12px rgba(13, 122, 118, 0.10) !important;
}
.st-key-accent_title input {
    color: #084c49 !important;
    font-weight: 700 !important;
}
.st-key-accent_title label p {
    color: #0d7a76 !important;
    font-weight: 700 !important;
}

/* Kolom Jumlah Cetak (Eksemplar): Hijau Gradasi Persis Side Menu */
.st-key-accent_qty label p {
    color: #0b6e6d !important;
    font-weight: 700 !important;
}
.st-key-accent_qty [data-testid="stNumberInputContainer"],
.st-key-accent_qty div[data-baseweb="input"],
.st-key-accent_qty div[data-baseweb="base-input"] {
    background: linear-gradient(95deg, #0b6e6d 0%, #178d89 100%) !important;
    border: none !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 18px -5px rgba(11, 110, 109, 0.42) !important;
}
.st-key-accent_qty input {
    background: transparent !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ffffff !important;
}
.st-key-accent_qty button {
    background: rgba(255, 255, 255, 0.16) !important;
    color: #ffffff !important;
    border: none !important;
}
.st-key-accent_qty button:hover {
    background: rgba(255, 255, 255, 0.28) !important;
    color: #ffffff !important;
}
.st-key-accent_qty button svg {
    fill: #ffffff !important;
    stroke: #ffffff !important;
}

.toner-scroll-box {
    max-height: 220px;
    overflow-y: auto;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(13, 122, 118, 0.22);
    border-radius: 12px;
    padding: 0.7rem 0.9rem;
    font-size: 0.78rem;
    line-height: 1.7;
    color: #1c3d3b;
    margin-top: 0.4rem;
}
.stat-grid-4 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr));
    gap: 14px;
    margin-bottom: 1.15rem;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
}
.stat-glass-box {
    background: rgba(238, 247, 245, 0.72);
    border: 1.5px solid rgba(255, 255, 255, 0.82);
    border-radius: 22px;
    padding: 1.05rem 1.15rem;
    display: flex;
    align-items: center;
    gap: 14px;
    box-shadow: 0 10px 22px -6px rgba(17, 60, 58, 0.06);
    min-width: 0;
    max-width: 100%;
    box-sizing: border-box;
}
.stat-badge {
    width: 46px;
    height: 46px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.stat-badge.purple { background: linear-gradient(135deg, #b597f6, #9b7af0); box-shadow: 0 6px 14px rgba(155, 122, 240, 0.28); }
.stat-badge.pink   { background: linear-gradient(135deg, #f982b6, #ec5f9b); box-shadow: 0 6px 14px rgba(236, 95, 155, 0.28); }
.stat-badge.orange { background: linear-gradient(135deg, #fcc176, #f5a34c); box-shadow: 0 6px 14px rgba(245, 163, 76, 0.28); }
.stat-badge.teal   { background: linear-gradient(135deg, #62a5a9, #3b8286); box-shadow: 0 6px 14px rgba(59, 130, 134, 0.28); }

.stat-meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1 1 0;
}
.stat-meta-label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #526c6d;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
    overflow-wrap: anywhere;
}
.stat-meta-val {
    font-size: 1.35rem;
    font-weight: 700;
    color: #162627;
    line-height: 1.15;
    white-space: normal;
    overflow-wrap: anywhere;
    font-variant-numeric: tabular-nums;
}

.page-stats-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    text-align: center;
    gap: 8px 4px;
}
.page-stats-grid > div {
    min-width: 0;
    overflow-wrap: anywhere;
}
@container (max-width: 320px) {
    .page-stats-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

.stat-bar-track {
    width: 100%;
    height: 8px;
    background: rgba(255, 255, 255, 0.88);
    border-radius: 99px;
    overflow: hidden;
    display: flex;
    margin: 0.45rem 0 0.9rem 0;
}
.stat-bar-fill-teal {
    background: #0d7a76;
    height: 100%;
}
.stat-bar-fill-pink {
    background: #f2748c;
    height: 100%;
}

.training-banner {
    background: linear-gradient(115deg, #095d5c 0%, #148582 60%, #106c6e 100%);
    border-radius: 24px;
    padding: 1.35rem 1.6rem;
    color: #ffffff;
    position: relative;
    overflow: hidden;
    box-shadow: 0 14px 28px -8px rgba(9, 93, 92, 0.38);
    margin-top: 0.4rem;
    margin-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.training-banner .sub {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.78);
}
.training-banner h4 {
    color: #ffffff;
    font-size: 1.2rem;
    font-weight: 700;
    line-height: 1.3;
    margin: 0.3rem 0 0.85rem 0;
}
.banner-pill-btn {
    display: inline-block;
    background: rgba(235, 247, 246, 0.94);
    color: #095d5c;
    font-size: 0.76rem;
    font-weight: 600;
    padding: 0.44rem 1rem;
    border-radius: 99px;
}

.stDownloadButton button, .stButton button {
    border-radius: 14px !important;
    font-weight: 600 !important;
    min-height: 44px !important;
}
.stDownloadButton button {
    background: rgba(255, 255, 255, 0.85) !important;
    border: 1px solid rgba(13, 122, 118, 0.22) !important;
    color: #0b625f !important;
}
.stDownloadButton button:hover {
    background: #ffffff !important;
    border-color: #0b625f !important;
}

.st-key-dl_pdf_color .stDownloadButton button {
    background: linear-gradient(135deg, #ff5e62 0%, #ff9966 32%, #f953c6 68%, #00d2ff 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 8px 18px -4px rgba(249, 83, 198, 0.38) !important;
}
.st-key-dl_pdf_color .stDownloadButton button p {
    color: #ffffff !important;
    font-weight: 700 !important;
}
.st-key-dl_pdf_color .stDownloadButton button:hover {
    filter: brightness(1.06) !important;
    color: #ffffff !important;
}

.st-key-dl_pdf_bw .stDownloadButton button {
    background: linear-gradient(135deg, #1f2424 0%, #3d4647 52%, #687375 100%) !important;
    color: #ffffff !important;
    border: none !important;
    box-shadow: 0 8px 18px -4px rgba(31, 36, 36, 0.34) !important;
}
.st-key-dl_pdf_bw .stDownloadButton button p {
    color: #ffffff !important;
    font-weight: 700 !important;
}
.st-key-dl_pdf_bw .stDownloadButton button:hover {
    filter: brightness(1.08) !important;
    color: #ffffff !important;
}

@media (min-width: 901px) and (max-width: 1200px) {
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar) {
        flex-basis: 250px !important;
        width: 250px !important;
    }
    .st-key-canvas_sidebar {
        padding: 1.5rem 1rem !important;
    }
    .st-key-canvas_main {
        padding-inline: 1.1rem !important;
    }
    .st-key-canvas_main > [data-testid="stHorizontalBlock"],
    .st-key-canvas_main > div > [data-testid="stHorizontalBlock"],
    .st-key-canvas_main > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    .st-key-canvas_main > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    .st-key-canvas_main > div > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"],
    .st-key-canvas_main > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    .stat-grid-4 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 900px) {
    /* Mobile uses document scrolling; release every desktop viewport lock. */
    html {
        height: auto !important;
        overflow-x: clip !important;
        overflow-y: auto !important;
    }
    body, #root {
        height: auto !important;
        min-height: 100% !important;
        overflow: visible !important;
    }
    .stApp, [data-testid="stAppViewContainer"] {
        position: relative !important;
        inset: auto !important;
        height: auto !important;
        min-height: 100vh !important;
        min-height: 100dvh !important;
        max-height: none !important;
        overflow: visible !important;
    }
    [data-testid="stMain"], .main {
        height: auto !important;
        max-height: none !important;
        overflow: visible !important;
        flex: none !important;
    }
    .block-container {
        height: auto !important;
        max-height: none !important;
        flex-shrink: 0 !important;
        width: 96vw !important;
        margin: 0.5rem auto !important;
        border-radius: 22px !important;
        overflow: hidden !important;
    }
    .block-container > [data-testid="stVerticalBlock"],
    .block-container > [data-testid="stVerticalBlockBorderWrapper"],
    .block-container > [data-testid="stVerticalBlockBorderWrapper"] > div,
    .block-container > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"],
    .block-container [data-testid="stLayoutWrapper"]:has(.st-key-canvas_shell),
    .st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_sidebar),
    .st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_main),
    .st-key-canvas_shell,
    .st-key-canvas_shell > div,
    .st-key-canvas_shell > div > [data-testid="stVerticalBlock"],
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar),
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main),
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar) > div,
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main) > div,
    .st-key-canvas_shell [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-canvas_sidebar) {
        height: auto !important;
    }
    .block-container [data-testid="stLayoutWrapper"]:has(.st-key-canvas_shell),
    .st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_sidebar),
    .st-key-canvas_shell [data-testid="stLayoutWrapper"]:has(.st-key-canvas_main) {
        flex: 1 1 auto !important;
    }
    .st-key-canvas_shell [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-canvas_sidebar) {
        flex-direction: column !important;
    }
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_sidebar),
    .st-key-canvas_shell [data-testid="stColumn"]:has(.st-key-canvas_main) {
        flex: 1 1 auto !important;
        width: 100% !important;
        padding: 0 !important;
    }
    .st-key-canvas_main [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap !important;
    }
    .st-key-canvas_main [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 100% !important;
        width: 100% !important;
    }
    .st-key-canvas_sidebar {
        height: auto !important;
        border-right: none;
        border-bottom: 1px solid rgba(255, 255, 255, 0.5);
        padding: 1.2rem !important;
        overflow: visible !important;
    }
    .st-key-canvas_sidebar[data-testid="stVerticalBlockBorderWrapper"] > div,
    .st-key-canvas_sidebar[data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        height: auto !important;
        gap: 1rem !important;
    }
    .st-key-canvas_main {
        height: auto !important;
        max-height: none !important;
        margin: 0 !important;
        padding: 1.2rem !important;
        overflow: visible !important;
        scrollbar-gutter: auto;
        overscroll-behavior-y: auto;
    }
    .stat-grid-4 {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .page-main-title {
        font-size: clamp(1.5rem, 5vw, 2.1rem) !important;
    }
}

@media (max-width: 540px) {
    .st-key-canvas_sidebar, .st-key-canvas_main {
        padding: 1rem !important;
    }
    .st-key-canvas_main [class*="st-key-card_"] {
        padding: 1rem !important;
    }
    .stat-grid-4 {
        grid-template-columns: minmax(0, 1fr);
        gap: 10px;
    }
    .stat-glass-box {
        padding: 1rem;
        gap: 12px;
    }
    .page-stats-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .topbar-wrap {
        align-items: flex-start !important;
    }
    .training-banner {
        padding: 1rem;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .training-banner > div:first-child {
        max-width: 100% !important;
    }
    .st-key-canvas_main [data-testid="stNumberInputContainer"] {
        min-height: 44px;
    }
}

@media (prefers-reduced-motion: reduce) {
    .st-key-canvas_shell * {
        scroll-behavior: auto !important;
        transition: none !important;
    }
}
</style>''', unsafe_allow_html=True)

CUBE_SVG = '<svg width="105" height="98" viewBox="0 0 110 105" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="72" cy="24" r="18" fill="#8be23b"/><rect x="18" y="34" width="28" height="28" rx="7" transform="rotate(-18 18 34)" fill="#ffffff" fill-opacity="0.92"/><rect x="64" y="52" width="26" height="26" rx="6" transform="rotate(22 64 52)" fill="#e8f8f7"/><circle cx="48" cy="76" r="8" fill="#b469ff"/><ellipse cx="62" cy="94" rx="38" ry="8" fill="#064544" fill-opacity="0.55"/></svg>'


def render_training_banner(sub_text="DON'T FORGET"):
    return (
        f'<div class="training-banner">'
        f'<div style="max-width: 66%;">'
        f'<div class="sub">{sub_text}</div>'
        f'<h4>Siapkan pracetak &amp; cek bleed 5mm</h4>'
        f'<span class="banner-pill-btn">Standar Produksi Litnus</span>'
        f'</div>'
        f'<div style="flex-shrink: 0;">{CUBE_SVG}</div>'
        f'</div>'
    )


# ==========================================
# STATE & HELPER FUNCTIONS
# ==========================================
def go_to(page):
    st.session_state['workspace'] = page


def draft_widget(widget, field, label, *args, **kwargs):
    stored = f'draft:{method}:{field}'
    key = f'widget:{stored}'
    if key not in st.session_state and stored in st.session_state:
        st.session_state[key] = st.session_state[stored]
        kwargs.pop('value', None)
        kwargs.pop('index', None)
    value = widget(label, *args, key=key, **kwargs)
    st.session_state[stored] = value
    return value


def reset_prelim_and_selection(method_name):
    for m in {method_name, 'Pilih halaman manual', 'Analisis warna otomatis'}:
        st.session_state[f'draft:{m}:roman'] = 0
        st.session_state[f'widget:draft:{m}:roman'] = 0
        st.session_state[f'draft:{m}:selection'] = ''
        st.session_state[f'widget:draft:{m}:selection'] = ''
    st.session_state.pop('analysis', None)
    st.session_state.pop('fc_toner_analysis', None)


def remember_pdf(upload_key, pdf_key, method_name):
    upload = st.session_state.get(upload_key)
    reset_prelim_and_selection(method_name)
    if upload is not None:
        st.session_state[pdf_key] = (upload.name, upload.getvalue())
        clean_title = os.path.splitext(upload.name)[0].replace('_', ' ').strip()
        if clean_title:
            stored_title = f'draft:{method_name}:title'
            widget_title = f'widget:{stored_title}'
            st.session_state[stored_title] = clean_title
            st.session_state[widget_title] = clean_title
    else:
        st.session_state.pop(pdf_key, None)


def remove_pdf(upload_key, pdf_key, method_name):
    st.session_state.pop(pdf_key, None)
    st.session_state.pop(upload_key, None)
    reset_prelim_and_selection(method_name)
    stored_title = f'draft:{method_name}:title'
    widget_title = f'widget:{stored_title}'
    st.session_state[stored_title] = 'Karya Terhebat'
    st.session_state[widget_title] = 'Karya Terhebat'


try:
    secrets = st.secrets.to_dict()
except FileNotFoundError:
    secrets = {}

configured = 'database' in secrets
version = 0
config = copy.deepcopy(DEFAULT)
if configured:
    try:
        setup()
        version, config = read()
    except Exception:
        st.error('Penyimpanan harga belum dapat diakses. Periksa koneksi database sebelum melanjutkan.')
        st.stop()

logged_in = st.user.get('is_logged_in', False)
admin = logged_in and st.user.get('email') in secrets.get('admin_emails', [])

if 'anon_name' not in st.session_state:
    st.session_state['anon_name'] = 'Tamu Studio'

screen = st.session_state.setdefault('workspace', 'Admin Tarif' if logged_in else 'Kalkulator Cepat')
if not logged_in and screen == 'Admin Tarif':
    screen = 'Kalkulator Cepat'
    st.session_state['workspace'] = 'Kalkulator Cepat'

if logged_in:
    raw_name = st.user.get('name') or st.user.get('email', 'User').split('@')[0]
    user_full_name = raw_name.strip()
else:
    user_full_name = st.session_state.get('anon_name', 'Tamu Studio').strip() or 'Tamu Studio'

initials = ''.join([part[0] for part in user_full_name.split()[:2]]).upper() or 'TS'

# ==========================================
# STRUKTUR FLOATING CANVAS: SIDEBAR (DIAM) + MAIN (SCROLLABLE)
# ==========================================
with st.container(key='canvas_shell'):
    col_nav, col_main = st.columns([0.24, 0.76], gap='small')

with col_nav:
    with st.container(key='canvas_sidebar'):
        with st.container():
            st.markdown('<div class="brand-logo">Litnus<span>Pro</span></div>', unsafe_allow_html=True)

            nav_menu = st.container(key='nav_menu')
            nav_admin = st.container(key='nav_admin') if logged_in else None

            for page, (method_name, path) in MENU.items():
                if page == 'Admin Tarif' and not logged_in:
                    continue
                active = screen == page
                icon_color = '#ffffff' if active else '#0d7a76'
                icon_uri = icon_data_uri(path, icon_color, 30)
                target_container = nav_menu if method_name else nav_admin
                with target_container:
                    st.button(
                        f'![](data:image/svg+xml,{icon_uri}) {page}',
                        key=f'btn_{page}',
                        type='primary' if active else 'secondary',
                        on_click=go_to,
                        args=(page,),
                        use_container_width=True,
                    )

        with st.container(key='nav_session'):
            sess_active = screen == 'Ganti Sesi'
            sess_icon_color = '#ffffff' if sess_active else '#0d7a76'
            sess_svg_path = '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>'
            sess_uri = icon_data_uri(sess_svg_path, sess_icon_color, 30)
            st.button(
                f'![](data:image/svg+xml,{sess_uri}) Keluar / Ganti Sesi',
                key='btn_switch_session',
                type='primary' if sess_active else 'secondary',
                on_click=go_to,
                args=('Ganti Sesi',),
                use_container_width=True,
            )

with col_main:
    with st.container(key='canvas_main'):
        search_svg = icon_svg('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>', '#0d7a76', 20)
        bell_svg = icon_svg('<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>', '#0d7a76', 20)

        st.markdown(
            f'<div class="topbar-wrap">'
            f'<div>'
            f'<div class="welcome-text">Welcome back, {user_full_name} 👋</div>'
            f'<h1 class="page-main-title">{screen}</h1>'
            f'</div>'
            f'<div class="user-profile-bar">'
            f'<span class="top-icon-btn">{search_svg}</span>'
            f'<span class="top-icon-btn">{bell_svg}</span>'
            f'<div class="user-chip">'
            f'<div class="user-avatar">{initials}</div>'
            f'<span class="user-name">{user_full_name}</span>'
            f'</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ==========================================
        # HALAMAN 0: KELUAR / GANTI SESI
        # ==========================================
        if screen == 'Ganti Sesi':
            col_sess_left, col_sess_right = st.columns(2, gap='medium')
            with col_sess_left:
                with st.container(key='card_session_google'):
                    lock_svg = icon_svg(MENU['Admin Tarif'][1], '#0d7a76', 36)
                    st.markdown(
                        f'<div class="card-header-row">'
                        f'<h3 class="card-title">Akun Google (Admin / Terdaftar)</h3>'
                        f'<span class="card-action-link">Google OAuth 2.0</span>'
                        f'</div>'
                        f'<div style="text-align: center; padding: 1.1rem 0.5rem 1rem 0.5rem;">'
                        f'<div style="display: inline-flex; padding: 14px; border-radius: 18px; background: rgba(13, 122, 118, 0.12); margin-bottom: 0.85rem;">'
                        f'{lock_svg}'
                        f'</div>'
                        f'<h3 style="margin: 0 0 0.4rem 0; font-weight: 700; color: #152627;">Sesi Akun Google</h3>'
                        f'<p style="margin: 0; font-size: 0.88rem; color: #4e6d6c;">'
                        f'Masuk menggunakan akun Google untuk membuka menu Admin Tarif dan sinkronisasi database.'
                        f'</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if logged_in:
                        st.success(f'Saat ini masuk sebagai **{user_full_name}**.')
                        if st.button('Keluar dari Akun Google', key='btn_do_google_logout', type='primary', use_container_width=True):
                            st.logout()
                    elif 'auth' in secrets:
                        if st.button('Masuk dengan Akun Google', key='btn_do_google_login', type='primary', use_container_width=True):
                            st.login()
                    else:
                        st.info('OAuth Google belum dikonfigurasi pada `secrets.toml`.')

            with col_sess_right:
                with st.container(key='card_session_guest'):
                    user_svg = icon_svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>', '#0d7a76', 36)
                    st.markdown(
                        f'<div class="card-header-row">'
                        f'<h3 class="card-title">Mode Tamu (Anonim)</h3>'
                        f'<span class="card-action-link">Akses Cepat Operator</span>'
                        f'</div>'
                        f'<div style="text-align: center; padding: 1.1rem 0.5rem 0.6rem 0.5rem;">'
                        f'<div style="display: inline-flex; padding: 14px; border-radius: 18px; background: rgba(13, 122, 118, 0.12); margin-bottom: 0.85rem;">'
                        f'{user_svg}'
                        f'</div>'
                        f'<h3 style="margin: 0 0 0.4rem 0; font-weight: 700; color: #152627;">Lanjutkan sebagai Tamu</h3>'
                        f'<p style="margin: 0; font-size: 0.88rem; color: #4e6d6c;">'
                        f'Gunakan kalkulator cepat dan pemisahan PDF tanpa login (menu Admin Tarif disembunyikan).'
                        f'</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    new_anon = st.text_input(
                        'Nama Lengkap / Tampilan Operator',
                        value=st.session_state['anon_name'],
                        placeholder='Ketik nama tampilan...',
                        key='input_anon_session_page',
                    )
                    if st.button('Lanjutkan sebagai Tamu Anonim', key='btn_continue_guest', type='primary', use_container_width=True):
                        st.session_state['anon_name'] = new_anon.strip() or 'Tamu Studio'
                        if logged_in:
                            st.logout()
                        else:
                            st.session_state['workspace'] = 'Kalkulator Cepat'
                            st.rerun()
            st.markdown(render_training_banner('PANDUAN PRACETAK'), unsafe_allow_html=True)
            st.stop()

        # ==========================================
        # HALAMAN 1: ADMIN TARIF
        # ==========================================
        if screen == 'Admin Tarif':
            if not admin:
                lock_svg = icon_svg(MENU['Admin Tarif'][1], '#0d7a76', 38)
                col_adm_left, col_adm_right = st.columns([1.15, 1], gap='medium')
                with col_adm_left:
                    with st.container(key='card_admin_login'):
                        st.markdown(
                            f'<div class="card-header-row">'
                            f'<h3 class="card-title">Otorisasi Ruang Admin</h3>'
                            f'<span class="card-action-link">Google OAuth 2.0</span>'
                            f'</div>'
                            f'<div style="text-align: center; padding: 1.4rem 0.5rem 1.2rem 0.5rem;">'
                            f'<div style="display: inline-flex; padding: 16px; border-radius: 20px; background: rgba(13, 122, 118, 0.12); margin-bottom: 1rem;">'
                            f'{lock_svg}'
                            f'</div>'
                            f'<h3 style="margin: 0 0 0.45rem 0; font-weight: 700; color: #152627;">Akses Pengaturan Tarif</h3>'
                            f'<p style="margin: 0; font-size: 0.9rem; color: #4e6d6c;">'
                            f'Masuk menggunakan akun Google Admin terdaftar untuk memperbarui matriks harga kertas, jilid, dan jenjang diskon.'
                            f'</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        if logged_in:
                            st.warning(f'Akun **{user_full_name}** belum terdaftar di `admin_emails`.')
                        elif 'auth' in secrets:
                            if st.button('Masuk dengan Google', key='google_login', type='primary', use_container_width=True):
                                st.login()
                        else:
                            st.info('OAuth Google belum dikonfigurasi pada secrets.toml.')
                        st.button('Kembali ke Kalkulator Cepat', key='guest_login', on_click=go_to, args=('Kalkulator Cepat',), use_container_width=True)

                with col_adm_right:
                    with st.container(key='card_admin_info'):
                        st.markdown(
                            f'<div class="card-header-row">'
                            f'<h3 class="card-title">Status Konfigurasi Saat Ini</h3>'
                            f'<span class="card-action-link">Versi v{version or 1}</span>'
                            f'</div>'
                            f'<div style="font-size: 0.88rem; color: #3d5a59; line-height: 1.65;">'
                            f'<p style="margin-bottom: 0.6rem;">• <b>Ukuran Default:</b> Unesco (15.5 x 23 cm)</p>'
                            f'<p style="margin-bottom: 0.6rem;">• <b>DP Tagihan:</b> {config["dp"]}% dari total pesanan</p>'
                            f'<p style="margin-bottom: 0.6rem;">• <b>Pengali Cetak:</b> Simplex {config["simplex"]}x | Hardcover {config["hardcover"]}x</p>'
                            f'<p style="margin-bottom: 0.2rem;">• <b>Diskon Finishing:</b> Bertahap {config["finishing_discount"]}% tiap {config["finishing_step"]} eks (Maks {config["finishing_cap"]}%)</p>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown(render_training_banner('PANDUAN PRACETAK'), unsafe_allow_html=True)
                st.stop()

            if not configured:
                st.info('Hubungkan database PostgreSQL di secrets.toml untuk menyimpan perubahan tarif.')
                st.stop()

            draft = copy.deepcopy(config)
            rows = []
            for sz, p in config['prices'].items():
                for paper in ['HVS 70', 'BP 57']:
                    rows.append(dict(Ukuran=sz, Kertas=paper, Warna=p[paper]['warna'], BW=p[paper]['bw'], Finishing=p['base_finishing_soft']))

            with st.container(key='card_admin_panel'):
                st.markdown(
                    '<div class="card-header-row">'
                    '<h3 class="card-title">1. Matriks Harga Kertas &amp; Jilid</h3>'
                    '<span class="card-action-link">Database Sync Aktif</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.caption('Nilai Finishing pada kedua baris kertas untuk ukuran yang sama harus sama.')
                edited = st.data_editor(
                    rows,
                    disabled=['Ukuran', 'Kertas'],
                    hide_index=True,
                    use_container_width=True,
                    height=240,
                )
                c1, c2, c3 = st.columns(3)
                draft['simplex'] = c1.number_input('Pengali simplex', min_value=0.1, value=float(config['simplex']))
                draft['hardcover'] = c2.number_input('Pengali hardcover', min_value=0.1, value=float(config['hardcover']))
                draft['dp'] = c3.number_input('DP (%)', 0, 100, int(config['dp']))

            with st.container(key='card_admin_tiers'):
                st.markdown(
                    '<div class="card-header-row">'
                    '<h3 class="card-title">2. Jenjang Diskon Eksemplar &amp; Finishing</h3>'
                    '<span class="card-action-link">Otomatisasi Diskon</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                draft['tiers'] = st.data_editor(
                    config['tiers'],
                    num_rows='dynamic',
                    key='tiers',
                    hide_index=True,
                    use_container_width=True,
                    height=200,
                )
                c1, c2, c3 = st.columns(3)
                draft['finishing_step'] = c1.number_input('Interval finishing', 1, value=int(config['finishing_step']))
                draft['finishing_discount'] = c2.number_input('Tambahan diskon (%)', 0, 100, int(config['finishing_discount']))
                draft['finishing_cap'] = c3.number_input('Batas diskon finishing (%)', 0, 100, int(config['finishing_cap']))

            with st.container(key='card_admin_save'):
                st.markdown(
                    '<div class="card-header-row">'
                    '<h3 class="card-title">3. Simulasi &amp; Simpan Perubahan</h3>'
                    '<span class="card-action-link">Verifikasi Tarif</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                try:
                    finishing = {}
                    for row in edited:
                        sz = row['Ukuran']
                        val = row['Finishing']
                        if sz in finishing and finishing[sz] != val:
                            raise ValueError('Finishing untuk ukuran yang sama harus konsisten.')
                        finishing[sz] = val
                        draft['prices'][sz]['base_finishing_soft'] = val
                        draft['prices'][sz][row['Kertas']] = {'warna': row['Warna'], 'bw': row['BW']}
                    validate(draft)
                    sim_size = 'Unesco (15.5 x 23 cm)' if 'Unesco (15.5 x 23 cm)' in config['prices'] else list(config['prices'])[0]
                    old = calculate(config, sim_size, 'HVS 70', 'Duplex (Bolak-balik)', 'Soft Cover', 10, 0, 100)
                    new = calculate(draft, sim_size, 'HVS 70', 'Duplex (Bolak-balik)', 'Soft Cover', 10, 0, 100)
                    st.metric(f'Simulasi 10 Eks ({sim_size.split()[0]} HVS 70, 100 BW)', rp(new['total']), rp(new['total'] - old['total']))
                    reason = st.text_input('Catatan alasan perubahan tarif')
                    if st.button('Simpan & Terapkan Perubahan Tarif', type='primary', disabled=not reason.strip(), use_container_width=True):
                        save(draft, version, reason.strip())
                        st.success('Tarif berhasil diperbarui.')
                        st.rerun()
                except (ValueError, TypeError, KeyError):
                    st.error('Pastikan format angka valid dan biaya finishing sama pada ukuran kertas yang sama.')

                with st.expander('Riwayat Perubahan Tarif'):
                    with connect() as c:
                        records = c.execute('SELECT created_at,actor,reason,old_data,new_data FROM litnus_history ORDER BY id DESC LIMIT 50').fetchall()
                    for date, actor, rsn, old_d, new_d in records:
                        with st.expander(f'{date} • {actor} • {rsn}'):
                            st.json({'sebelum': old_d, 'sesudah': new_d})
            st.stop()

        # ==========================================
        # HALAMAN 2: WORKSPACE KALKULATOR & PDF
        # ==========================================
        method = MENU[screen][0]
        col_left, col_right = st.columns([1.15, 1], gap='medium')

        with col_left:
            uploaded = None
            color = bw = 0
            cb = bb = None
            colors = []
            blacks = []
            page_toner_pcts = {}
            roman = 0
            selection = ''
            force = False
            full_color_complexity_mode = False
            manual_toner_pct = 35.0
            sensitivity = 25
            pct = 0.10
            run_analysis_clicked = False

            with st.container(key='card_naskah'):
                st.markdown(
                    f'<div class="card-header-row">'
                    f'<h3 class="card-title">Naskah &amp; Halaman</h3>'
                    f'<span class="card-action-link">{method}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if method != 'Jumlah halaman saja':
                    upload_key, pdf_key = f'upload:{method}', f'pdf:{method}'
                    st.file_uploader(
                        'Unggah PDF isi buku (Maks 200MB)',
                        type='pdf',
                        key=upload_key,
                        on_change=remember_pdf,
                        args=(upload_key, pdf_key, method),
                    )
                    uploaded = st.session_state.get(pdf_key)
                    default_book_title = os.path.splitext(uploaded[0])[0].replace('_', ' ') if uploaded else 'Karya Terhebat'

                    with st.container(key='accent_title'):
                        title = draft_widget(st.text_input, 'title', 'Judul buku (otomatis dari nama PDF)', value=default_book_title)

                    if uploaded:
                        st.caption(f'📄 Berkas aktif: **{uploaded[0]}**')
                        st.button('Lepas PDF', key=f'remove:{method}', on_click=remove_pdf, args=(upload_key, pdf_key, method))

                    if method == 'Analisis warna otomatis':
                        st.markdown(
                            '<div style="font-size: 0.84rem; font-weight: 700; color: #0d7a76; margin: 0.55rem 0 0.35rem 0;">'
                            '🎨 Parameter Deteksi Warna &amp; Kompleksitas Toner</div>',
                            unsafe_allow_html=True,
                        )
                        force = draft_widget(
                            st.checkbox,
                            'force_bw',
                            'Paksa SEMUA Halaman Menjadi BW',
                            value=False,
                        )
                        full_color_complexity_mode = draft_widget(
                            st.checkbox,
                            'full_color_complexity',
                            'Cetak Full Colour — Hitung Harga Proporsional % Kompleksitas Toner Warna Tiap Halaman',
                            value=False,
                            disabled=force,
                            help=(
                                'Mode Auto-Detect Full Colour: Semua halaman dicetak berwarna, namun harga tiap halaman '
                                'otomatis dikurangi secara proporsional mengikuti % cakupan blok warna di halaman tersebut.'
                            ),
                        )

                        sliders_disabled = bool(force or full_color_complexity_mode)

                        sc1, sc2 = st.columns(2)
                        sensitivity = draft_widget(
                            sc1.slider,
                            'sensitivity',
                            'Batas Kontras Warna',
                            min_value=5,
                            max_value=50,
                            value=25,
                            step=5,
                            disabled=sliders_disabled,
                        )
                        pct = draft_widget(
                            sc2.slider,
                            'pct',
                            'Batas Minimum Area Warna (%)',
                            min_value=0.01,
                            max_value=5.00,
                            value=0.10,
                            step=0.05,
                            disabled=sliders_disabled,
                        )
                        run_analysis_clicked = st.button(
                            'Jalankan Analisis PDF',
                            type='primary',
                            disabled=not uploaded,
                            use_container_width=True,
                        )
                    elif method == 'Pilih halaman manual':
                        roman = draft_widget(
                            st.number_input,
                            'roman',
                            'Jumlah halaman preliminaries (Romawi)',
                            min_value=0,
                            value=0,
                            step=1,
                        )
                        selection = draft_widget(
                            st.text_area,
                            'selection',
                            'Daftar halaman warna',
                            placeholder='Contoh: iii-v, 1, 5-9',
                        )
                else:
                    with st.container(key='accent_title'):
                        title = draft_widget(st.text_input, 'title', 'Judul buku', value='Karya Terhebat')
                    ca, cb_col = st.columns(2)
                    color = draft_widget(ca.number_input, 'color', 'Halaman warna', min_value=0, value=0)
                    bw = draft_widget(cb_col.number_input, 'bw', 'Halaman BW', min_value=0, value=0)
                    full_color_complexity_mode = draft_widget(
                        st.checkbox,
                        'manual_fc_complexity',
                        'Cetak Full Colour — Kurangi harga berdasarkan rata-rata % kompleksitas toner warna',
                        value=False,
                    )
                    if full_color_complexity_mode and (color + bw) > 0:
                        manual_toner_pct = draft_widget(
                            st.slider,
                            'manual_toner_pct',
                            'Rata-rata kompleksitas / cakupan toner warna per halaman (%)',
                            min_value=1.0,
                            max_value=100.0,
                            value=35.0,
                            step=1.0,
                        )
                        total_man = color + bw
                        color = total_man
                        bw = 0
                        page_toner_pcts = {
                            pno: float(manual_toner_pct)
                            for pno in range(1, total_man + 1)
                        }

                toner_detail_placeholder = st.empty()

            with st.container(key='card_spek'):
                st.markdown(
                    '<div class="card-header-row">'
                    '<h3 class="card-title">Spesifikasi Produksi</h3>'
                    '<span class="card-action-link">Standar Offset/POD</span>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                size_options = list(config['prices'].keys())
                unesco_idx = next((i for i, s in enumerate(size_options) if 'Unesco' in s), 0)

                sa, sb = st.columns(2)
                size = draft_widget(sa.selectbox, 'size', 'Ukuran buku', options=size_options, index=unesco_idx)
                paper = draft_widget(sb.selectbox, 'paper', 'Jenis kertas', options=['HVS 70', 'BP 57'])
                mode = draft_widget(sa.selectbox, 'mode', 'Mode cetak', options=['Duplex (Bolak-balik)', 'Simplex (Satu Sisi)'])
                binding = draft_widget(sb.selectbox, 'binding', 'Tipe jilid', options=['Soft Cover', 'Hard Cover'])

                with st.container(key='accent_qty'):
                    qty = draft_widget(st.number_input, 'qty', 'Jumlah cetak (eksemplar)', min_value=1, value=1)

                override = None
                if admin:
                    with st.expander('Diskon khusus admin'):
                        if draft_widget(st.checkbox, 'override_enabled', 'Terapkan diskon manual'):
                            override = draft_widget(st.number_input, 'override', 'Diskon isi (%)', min_value=0, max_value=100, value=0)

                if uploaded:
                    data = uploaded[1]
                    try:
                        total = get_pdf_page_count(data)
                        st.caption(f'Total terdeteksi: **{total} halaman PDF**')
                        if method == 'Analisis warna otomatis':
                            file_hash = hashlib.sha256(data).hexdigest()

                            if full_color_complexity_mode and not force:
                                fc_sig = ('v2_block_cov', file_hash, total)
                                saved_fc = st.session_state.get('fc_toner_analysis')
                                if run_analysis_clicked or not saved_fc or saved_fc[:3] != fc_sig:
                                    st.session_state['fc_toner_analysis'] = (
                                        *fc_sig,
                                        analyze_full_color_toner_pdf(data, total),
                                    )
                                    saved_fc = st.session_state.get('fc_toner_analysis')
                                colors, blacks, cb, bb, page_toner_pcts = saved_fc[3]
                            else:
                                current_sig = (file_hash, mode, force, sensitivity, pct)
                                saved = st.session_state.get('analysis')

                                if run_analysis_clicked:
                                    with st.spinner('Memindai spektrum halaman...'):
                                        st.session_state['analysis'] = (
                                            *current_sig,
                                            process_and_split_pdf(data, force, sensitivity, pct, mode, total),
                                        )
                                    saved = st.session_state.get('analysis')

                                if saved and saved[:5] == current_sig:
                                    unpacked = saved[5]
                                    colors, blacks, cb, bb, raw_color_pages = unpacked[:5]
                                    if mode == 'Duplex (Bolak-balik)' and raw_color_pages and set(raw_color_pages) != set(colors):
                                        st.success('🔄 Duplex aktif: halaman pasangan otomatis ikut dimasukkan ke hasil warna.')
                                else:
                                    st.info('Tekan tombol "Jalankan Analisis PDF" pada kartu Naskah & Halaman untuk menghitung halaman.')
                                    colors, blacks, page_toner_pcts = [], [], {}
                        else:
                            if roman > total:
                                raise ValueError(f'Preliminaries ({roman}) melebihi total halaman ({total}).')
                            pair = draft_widget(st.checkbox, 'pair', 'Otomatis sertakan pasangan lembar duplex', value=True, disabled=mode.startswith('Simplex'))
                            colors, _, errors, _ = parse_page_input(selection, total, roman)
                            if errors:
                                st.error(' • '.join(errors))
                                st.stop()
                            if colors:
                                if pair and mode.startswith('Duplex'):
                                    colors = add_duplex_pairs(colors, total)
                                colors, blacks, cb, bb = split_pdf_by_pages(data, tuple(colors), total)
                        color, bw = len(colors), len(blacks)
                    except (ValueError, RuntimeError) as e:
                        st.error(str(e))
                        st.stop()

                if colors or blacks:
                    with toner_detail_placeholder.container():
                        with st.expander('📊 Lihat daftar sebaran nomor halaman & persentase toner warna', expanded=bool(full_color_complexity_mode)):
                            if page_toner_pcts and colors:
                                all_toner_items = ', '.join(
                                    f'<b>Hlm {p}:</b> {page_toner_pcts.get(p, 0.0):.1f}%'
                                    for p in colors
                                )
                                st.markdown(
                                    f'<div style="font-size:0.8rem; font-weight:700; color:#0d7a76;">'
                                    f'Rincian Cakupan Warna Seluruh Halaman (1 s/d {len(colors)}):</div>'
                                    f'<div class="toner-scroll-box">{all_toner_items}</div>',
                                    unsafe_allow_html=True,
                                )
                            st.write('**Halaman Warna:**', ', '.join(map(str, colors)) or 'Tidak ada')
                            st.write('**Halaman Hitam Putih:**', ', '.join(map(str, blacks)) or 'Tidak ada')

        with col_right:
            total_pages_count = color + bw
            color_ratio_pct = int(round((color / total_pages_count) * 100)) if total_pages_count > 0 else 0
            bw_ratio_pct = 100 - color_ratio_pct if total_pages_count > 0 else 100

            with st.container(key='card_total'):
                r = calculate_with_toner_complexity(
                    config,
                    size,
                    paper,
                    mode,
                    binding,
                    qty,
                    color,
                    bw,
                    override=override,
                    full_color_complexity_mode=full_color_complexity_mode,
                    page_toner_pcts=page_toner_pcts,
                ) if total_pages_count > 0 else {
                    'unit': 0, 'total': 0, 'dp': 0, 'discount': 0, 'finishing_discount': 0,
                    'finishing': 0, 'color_rate': 0, 'bw_rate': 0, 'full': 0,
                    'avg_toner_pct': 0.0, 'toner_savings_total': 0, 'toner_savings_unit': 0, 'avg_page_rate': 0,
                }

                st.markdown(
                    f'<div class="card-header-row">'
                    f'<h3 class="card-title">Statistik &amp; Ringkasan Biaya</h3>'
                    f'<span class="card-action-link">{size.split()[0]} • {paper}</span>'
                    f'</div>'
                    f'<div style="background: rgba(255,255,255,0.52); border: 1px solid rgba(255,255,255,0.82); border-radius: 18px; padding: 1rem 1rem; margin-bottom: 0.9rem;">'
                    f'<div class="stat-bar-track">'
                    f'<div class="stat-bar-fill-teal" style="width: {bw_ratio_pct}%;"></div>'
                    f'<div class="stat-bar-fill-pink" style="width: {color_ratio_pct}%;"></div>'
                    f'</div>'
                    f'<div class="page-stats-grid">'
                    f'<div><div style="font-size: 0.62rem; font-weight: 600; color: #526c6d;">TOTAL HAL</div><div style="font-size: 0.98rem; font-weight: 700; color: #162627;">{total_pages_count}</div></div>'
                    f'<div><div style="font-size: 0.62rem; font-weight: 600; color: #526c6d;">HITAM PUTIH</div><div style="font-size: 0.98rem; font-weight: 700; color: #0d7a76;">{bw}</div></div>'
                    f'<div><div style="font-size: 0.62rem; font-weight: 600; color: #526c6d;">WARNA</div><div style="font-size: 0.98rem; font-weight: 700; color: #e25c86;">{color}</div></div>'
                    f'<div><div style="font-size: 0.62rem; font-weight: 600; color: #526c6d;">DISKON ISI</div><div style="font-size: 0.98rem; font-weight: 700; color: #0d7a76;">{r["discount"]}%</div></div>'
                    f'<div><div style="font-size: 0.62rem; font-weight: 600; color: #526c6d;">DISK. FINISH</div><div style="font-size: 0.98rem; font-weight: 700; color: #0d7a76;">{r["finishing_discount"]}%</div></div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                if full_color_complexity_mode and total_pages_count > 0:
                    st.markdown(
                        f'<div style="background: rgba(13, 122, 118, 0.10); border: 1px solid rgba(13, 122, 118, 0.25); '
                        f'border-radius: 14px; padding: 0.75rem 0.95rem; margin-bottom: 0.85rem; font-size: 0.8rem; color: #0b5855; line-height: 1.55;">'
                        f'🎨 <b>Auto-Detect Full Colour Aktif:</b> Rata-rata cakupan warna <b>{r["avg_toner_pct"]}%</b>/hlm • '
                        f'Tarif efektif rata-rata <b>{rp(r["avg_page_rate"])}/hlm</b> (dari tarif blok 100% {rp(r["color_rate"])}/hlm) • '
                        f'Hemat <b>{rp(r["toner_savings_unit"])}/eks</b> (Total hemat <b>{rp(r["toner_savings_total"])}</b>)'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                if total_pages_count > 0:
                    c_dl1, c_dl2 = st.columns(2)
                    toner_note = (
                        f"\nMode Full Colour Proporsional: Rata-rata cakupan warna {r['avg_toner_pct']}% | Tarif efektif {rp(r['avg_page_rate'])}/hlm (Hemat {rp(r['toner_savings_total'])})"
                        if full_color_complexity_mode else ""
                    )
                    receipt = f"""LITNUS PRINTING - ESTIMASI BIAYA
Judul: {title}
Tarif versi: {version}
Spesifikasi: {size} | {paper} | {mode} | {binding}
Isi buku: {color} halaman warna + {bw} BW{toner_note}
Jumlah: {qty} eksemplar
Harga/eks: {rp(r['unit'])}
Total: {rp(r['total'])}
DP {config['dp']}%: {rp(r['dp'])}
Diskon isi: {r['discount']}% | Diskon finishing: {r['finishing_discount']}%"""
                    c_dl1.download_button('Unduh Estimasi', receipt, f'Estimasi_{title}.txt', 'text/plain', use_container_width=True)

                    invoice = f"""LITNUS PRINTING - NOTA TAGIHAN CETAK
Pemesan: {user_full_name}
Judul buku: {title}
Spesifikasi: {size} | {paper} | {mode} | {binding}
Isi buku: {color} halaman warna + {bw} halaman hitam putih ({qty} eksemplar){toner_note}
Harga per eksemplar: {rp(r['unit'])}
Diskon isi: {r['discount']}% | Diskon finishing: {r['finishing_discount']}%
TOTAL TAGIHAN: {rp(r['total'])}
DP {config['dp']}%: {rp(r['dp'])} | Sisa: {rp(r['total'] - r['dp'])}

Rekening PT Literasi Nusantara Abadi Grup:
- Mandiri: 144-00-2306065-7
- BCA: 117-737-3737"""
                    c_dl2.download_button('Unduh Nota TXT', invoice, f'Nota_{title}.txt', 'text/plain; charset=utf-8', use_container_width=True)

                    if cb or bb:
                        cp1, cp2 = st.columns(2)
                        if cb:
                            with cp1:
                                with st.container(key='dl_pdf_color'):
                                    st.download_button('PDF Warna', cb, f'{title}_Warna.pdf', 'application/pdf', use_container_width=True)
                        if bb:
                            with cp2:
                                with st.container(key='dl_pdf_bw'):
                                    st.download_button('PDF Hitam Putih', bb, f'{title}_BW.pdf', 'application/pdf', use_container_width=True)

            svg_pie = icon_svg('<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>', '#ffffff', 24)
            svg_tag = icon_svg('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>', '#ffffff', 24)
            svg_wallet = icon_svg('<rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>', '#ffffff', 24)
            svg_star = icon_svg('<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>', '#ffffff', 24)

            stat_label_1 = 'CAKUPAN WARNA' if full_color_complexity_mode else 'RASIO WARNA'
            stat_val_1 = f'{r["avg_toner_pct"]}%' if full_color_complexity_mode else f'{color_ratio_pct}%'

            st.markdown(
                f'<div class="stat-grid-4">'
                f'<div class="stat-glass-box"><div class="stat-badge purple">{svg_pie}</div><div class="stat-meta"><span class="stat-meta-label">{stat_label_1}</span><span class="stat-meta-val">{stat_val_1}</span></div></div>'
                f'<div class="stat-glass-box"><div class="stat-badge pink">{svg_tag}</div><div class="stat-meta"><span class="stat-meta-label">TOTAL TAGIHAN</span><span class="stat-meta-val" style="font-size: 1.18rem;">{rp(r["total"])}</span></div></div>'
                f'<div class="stat-glass-box"><div class="stat-badge orange">{svg_wallet}</div><div class="stat-meta"><span class="stat-meta-label">DP ({config["dp"]}%)</span><span class="stat-meta-val" style="font-size: 1.18rem;">{rp(r["dp"])}</span></div></div>'
                f'<div class="stat-glass-box"><div class="stat-badge teal">{svg_star}</div><div class="stat-meta"><span class="stat-meta-label">HARGA / EKS</span><span class="stat-meta-val" style="font-size: 1.18rem;">{rp(r["unit"])}</span></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # BANNER KANAN BAWAH
            st.markdown(render_training_banner("DON'T FORGET"), unsafe_allow_html=True)
