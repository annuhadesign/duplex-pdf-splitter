import fitz  # PyMuPDF
import os
import re
import streamlit as st
from datetime import datetime, timedelta, timezone

# ============================================================
# LITNUS PRINTING
# PDF SPLITTER & COST CALCULATOR
# ============================================================

st.set_page_config(
    page_title="Litnus Printing - Production Calculator",
    page_icon="🖨️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# THEME STATE
# ============================================================

if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"


def toggle_theme():
    st.session_state.theme_mode = (
        "light" if st.session_state.theme_mode == "dark" else "dark"
    )


# ============================================================
# DESIGN SYSTEM
# ============================================================

CSS_DARK_MODE = """
<style>
:root {
    --bg: #070b12;
    --panel: rgba(15, 23, 42, .70);
    --panel2: rgba(17, 31, 51, .72);
    --border: rgba(255,255,255,.09);
    --text: #e5edf7;
    --muted: #8fa3b8;
    --accent: #10b981;
    --accent2: #22d3ee;
    --gold: #facc15;
}
.stApp {
    background:
        radial-gradient(circle at 8% 10%, rgba(16,185,129,.18), transparent 32%),
        radial-gradient(circle at 92% 18%, rgba(34,211,238,.14), transparent 30%),
        radial-gradient(circle at 52% 92%, rgba(99,102,241,.12), transparent 36%),
        #070b12;
    color: var(--text);
}
.block-container { padding-top: 1.3rem; max-width: 1500px; }
h1,h2,h3 { color: #fff !important; }
p, label, span { color: var(--text); }
section[data-testid="stSidebar"] {
    background: rgba(8,15,27,.72) !important;
    backdrop-filter: blur(22px);
    border-right: 1px solid var(--border);
}
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, rgba(20,35,53,.82), rgba(10,20,34,.70)) !important;
    border: 1px solid rgba(255,255,255,.08) !important;
    border-radius: 18px !important;
    padding: 18px !important;
    box-shadow: 0 12px 35px rgba(0,0,0,.28);
}
div[data-testid="stMetricLabel"] { color:#8fa3b8 !important; }
div[data-testid="stMetricValue"] { color:#5eead4 !important; }
.stButton > button, .stDownloadButton > button {
    border: 0 !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
}
.stButton > button {
    background: linear-gradient(135deg,#10b981,#059669) !important;
    color:#02140f !important;
    box-shadow: 0 8px 25px rgba(16,185,129,.20);
}
.stDownloadButton > button {
    background: linear-gradient(135deg,#0ea5e9,#06b6d4) !important;
    color:white !important;
}
div[data-testid="stFileUploader"],
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea, input {
    border-radius: 12px !important;
}
div[data-testid="stAlert"] { border-radius: 14px; }
.glass-card {
    background: linear-gradient(145deg, rgba(18,32,50,.78), rgba(10,20,34,.62));
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 20px;
    padding: 22px;
    margin: 8px 0 18px;
    box-shadow: 0 15px 40px rgba(0,0,0,.20);
    backdrop-filter: blur(18px);
}
.hero {
    padding: 28px 30px;
    border-radius: 24px;
    background:
        linear-gradient(120deg, rgba(16,185,129,.18), rgba(14,165,233,.10)),
        rgba(9,17,29,.70);
    border: 1px solid rgba(94,234,212,.15);
    box-shadow: 0 18px 55px rgba(0,0,0,.22);
    margin-bottom: 18px;
}
.hero-kicker { color:#5eead4; font-weight:800; letter-spacing:1.5px; font-size:13px; }
.hero-title { color:#fff; font-size:34px; font-weight:900; margin:3px 0; }
.hero-sub { color:#a7b7c9; font-size:15px; }
.pill {
    display:inline-block;
    padding:6px 11px;
    border-radius:999px;
    background:rgba(16,185,129,.12);
    border:1px solid rgba(16,185,129,.22);
    color:#6ee7b7;
    font-size:12px;
    font-weight:700;
    margin:4px 5px 0 0;
}
.section-title { font-size:18px; font-weight:800; color:#fff; margin:12px 0; }
.result-card {
    border-radius:18px;
    padding:18px;
    border:1px solid rgba(255,255,255,.08);
    background:rgba(15,27,43,.70);
}
.result-color { border-color:rgba(16,185,129,.35); }
.result-bw { border-color:rgba(96,165,250,.25); }
.page-list {
    max-height:180px;
    overflow:auto;
    padding:12px;
    border-radius:12px;
    background:rgba(0,0,0,.16);
    font-family:monospace;
    font-size:12px;
    color:#cbd5e1;
}
button[title="Toggle Theme"] {
    position: fixed !important;
    right: 28px !important;
    bottom: 28px !important;
    z-index: 999999 !important;
    width: 58px !important;
    height: 58px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    background:rgba(20,35,53,.94) !important;
    color:white !important;
    border:1px solid rgba(255,255,255,.14) !important;
    box-shadow:0 10px 30px rgba(0,0,0,.45) !important;
}
.footer {
    text-align:center;
    color:#718096;
    padding:18px 0 5px;
    font-size:12px;
}
</style>
"""

CSS_LIGHT_MODE = """
<style>
.stApp {
    background:
        radial-gradient(circle at 8% 10%, rgba(186,230,253,.60), transparent 32%),
        radial-gradient(circle at 92% 18%, rgba(254,205,211,.55), transparent 30%),
        radial-gradient(circle at 52% 92%, rgba(221,214,254,.65), transparent 36%),
        #f3f6fb;
    color:#1e293b;
}
.block-container { padding-top:1.3rem; max-width:1500px; }
h1,h2,h3 { color:#0f172a !important; }
p,label,span { color:#475569; }
section[data-testid="stSidebar"] {
    background:rgba(255,255,255,.78) !important;
    backdrop-filter:blur(22px);
    border-right:1px solid rgba(255,255,255,.9);
}
div[data-testid="stMetric"] {
    background:linear-gradient(145deg,#ffffff,#f8fafc) !important;
    border:1px solid rgba(148,163,184,.18) !important;
    border-radius:18px !important;
    padding:18px !important;
    box-shadow:0 12px 30px rgba(15,23,42,.08);
}
div[data-testid="stMetricLabel"] { color:#64748b !important; }
div[data-testid="stMetricValue"] { color:#059669 !important; }
.stButton > button {
    background:linear-gradient(135deg,#8b5cf6,#ec4899) !important;
    color:white !important;
    border:0 !important;
    border-radius:12px !important;
    font-weight:700 !important;
}
.stDownloadButton > button {
    background:linear-gradient(135deg,#0284c7,#06b6d4) !important;
    color:white !important;
    border:0 !important;
    border-radius:12px !important;
    font-weight:700 !important;
}
div[data-testid="stFileUploader"],
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
textarea,input { border-radius:12px !important; }
.glass-card {
    background:rgba(255,255,255,.70);
    border:1px solid rgba(255,255,255,.95);
    border-radius:20px;
    padding:22px;
    margin:8px 0 18px;
    box-shadow:0 15px 40px rgba(15,23,42,.08);
    backdrop-filter:blur(18px);
}
.hero {
    padding:28px 30px;
    border-radius:24px;
    background:linear-gradient(120deg,rgba(255,255,255,.82),rgba(241,245,249,.70));
    border:1px solid rgba(255,255,255,.95);
    box-shadow:0 18px 50px rgba(15,23,42,.08);
    margin-bottom:18px;
}
.hero-kicker { color:#059669; font-weight:800; letter-spacing:1.5px; font-size:13px; }
.hero-title { color:#0f172a; font-size:34px; font-weight:900; margin:3px 0; }
.hero-sub { color:#64748b; font-size:15px; }
.pill {
    display:inline-block;
    padding:6px 11px;
    border-radius:999px;
    background:rgba(16,185,129,.10);
    border:1px solid rgba(16,185,129,.20);
    color:#047857;
    font-size:12px;
    font-weight:700;
    margin:4px 5px 0 0;
}
.section-title { font-size:18px; font-weight:800; color:#0f172a; margin:12px 0; }
.result-card {
    border-radius:18px;
    padding:18px;
    border:1px solid rgba(148,163,184,.18);
    background:rgba(255,255,255,.72);
}
.result-color { border-color:rgba(16,185,129,.30); }
.result-bw { border-color:rgba(59,130,246,.22); }
.page-list {
    max-height:180px;
    overflow:auto;
    padding:12px;
    border-radius:12px;
    background:rgba(241,245,249,.75);
    font-family:monospace;
    font-size:12px;
    color:#334155;
}
button[title="Toggle Theme"] {
    position:fixed !important;
    right:28px !important;
    bottom:28px !important;
    z-index:999999 !important;
    width:58px !important;
    height:58px !important;
    border-radius:50% !important;
    padding:0 !important;
    background:rgba(255,255,255,.95) !important;
    color:#0f172a !important;
    border:1px solid rgba(255,255,255,1) !important;
    box-shadow:0 10px 30px rgba(15,23,42,.15) !important;
}
.footer { text-align:center; color:#94a3b8; padding:18px 0 5px; font-size:12px; }
</style>
"""

if st.session_state.theme_mode == "dark":
    st.markdown(CSS_DARK_MODE, unsafe_allow_html=True)
    theme_icon = "☀️"
else:
    st.markdown(CSS_LIGHT_MODE, unsafe_allow_html=True)
    theme_icon = "🌙"

st.button(theme_icon, on_click=toggle_theme, help="Ganti tema")


# ============================================================
# PRICING MATRIX
# ============================================================

PRICING_MATRIX = {
    "A5 (14.8 x 21 cm)": {
        "base_finishing_soft": 25000,
        "HVS 70": {"warna": 500, "bw": 150},
        "BP 57": {"warna": 550, "bw": 180},
    },
    "Unesco (15.5 x 23 cm)": {
        "base_finishing_soft": 27000,
        "HVS 70": {"warna": 600, "bw": 160},
        "BP 57": {"warna": 650, "bw": 200},
    },
    "B5 ISO (17.6 x 25 cm)": {
        "base_finishing_soft": 30000,
        "HVS 70": {"warna": 800, "bw": 180},
        "BP 57": {"warna": 850, "bw": 210},
    },
    "B5 JIS (18.2 x 25.7 cm)": {
        "base_finishing_soft": 31000,
        "HVS 70": {"warna": 900, "bw": 190},
        "BP 57": {"warna": 950, "bw": 220},
    },
    "A4 (21 x 29.7 cm)": {
        "base_finishing_soft": 31000,
        "HVS 70": {"warna": 1000, "bw": 200},
        "BP 57": {"warna": 1100, "bw": 250},
    },
}


# ============================================================
# HELPERS
# ============================================================

def format_rupiah(value):
    return f"Rp {int(value):,}".replace(",", ".")


ROMAN_VALUES = {
    "I": 1,
    "V": 5,
    "X": 10,
    "L": 50,
    "C": 100,
    "D": 500,
    "M": 1000,
}


def int_to_roman(number):
    if number <= 0:
        return ""
    pairs = [
        (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
        (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    result = []
    for value, symbol in pairs:
        while number >= value:
            result.append(symbol)
            number -= value
    return "".join(result)


def roman_to_int(value):
    value = value.upper()
    if not value or not re.fullmatch(r"[IVXLCDM]+", value):
        return None

    total = 0
    prev = 0
    for char in reversed(value):
        current = ROMAN_VALUES[char]
        if current < prev:
            total -= current
        else:
            total += current
            prev = current

    # Strict validation prevents strings such as IIX from being accepted.
    if int_to_roman(total) != value:
        return None

    return total


def is_roman_token(token):
    return bool(re.fullmatch(r"[ivxlcdmIVXLCDM]+", token))


def expand_page_token(token):
    """
    Returns:
        ("roman", [numbers]) or ("arabic", [numbers]) or ("error", message)

    Examples:
        iii     -> ("roman", [3])
        iii-vii -> ("roman", [3,4,5,6,7])
        8       -> ("arabic", [8])
        8-12    -> ("arabic", [8,9,10,11,12])
    """
    token = token.strip()

    if not token:
        return "error", "Token kosong"

    # Roman range, e.g. iii-vii
    if "-" in token:
        parts = token.split("-")
        if len(parts) != 2:
            return "error", f"Format tidak dikenali: {token}"

        left, right = parts[0], parts[1]

        if is_roman_token(left) and is_roman_token(right):
            a = roman_to_int(left)
            b = roman_to_int(right)
            if a is None or b is None:
                return "error", f"Romawi tidak valid: {token}"
            if a > b:
                a, b = b, a
            return "roman", list(range(a, b + 1))

        # Arabic range, e.g. 8-12
        if left.isdigit() and right.isdigit():
            a, b = int(left), int(right)
            if a > b:
                a, b = b, a
            return "arabic", list(range(a, b + 1))

        return "error", f"Format range tidak dikenali: {token}"

    # Roman single page
    if is_roman_token(token):
        value = roman_to_int(token)
        if value is None:
            return "error", f"Romawi tidak valid: {token}"
        return "roman", [value]

    # Arabic single page
    if token.isdigit():
        return "arabic", [int(token)]

    return "error", f"Format tidak dikenali: {token}"


def parse_page_input(text, total_pages, roman_count):
    """
    Manual page selector dengan offset Romawi.

    Aturan:
      - Roman: iii -> PDF 3
      - Arabic: 8 -> PDF (roman_count + 8)
      - Jadi jika roman_count = 12:
            xii -> PDF 12
            3   -> PDF 15
            8   -> PDF 20

    Mendukung:
      iii, v, xii, 3, 8
      iii-vii, 3-8
      iii-vii, 3-8, xii, 20
    """
    if not text or not text.strip():
        return [], [], [], []

    if roman_count < 0:
        return [], [], [], ["Jumlah halaman Romawi tidak valid."]

    # Normalisasi input agar bisa dipaste dari Excel/Word/PDF dalam
    # format horizontal maupun vertikal.
    #
    # Didukung:
    #   i, iii, v, 2, 47
    #   i\niii\nv\n2\n47
    #   i iii v 2 47
    #   iii-vii, 3-8
    #   iii - vii
    #
    # En dash / em dash juga dinormalisasi menjadi "-" agar range
    # hasil copy-paste tetap dikenali.
    normalized_text = (
        text
        .replace("–", "-")
        .replace("—", "-")
    )

    # Hilangkan spasi di sekitar tanda range supaya
    # "iii - vii" menjadi "iii-vii".
    normalized_text = re.sub(r"\s*-\s*", "-", normalized_text)

    # Koma, titik koma, whitespace, tab, dan newline semuanya
    # diperlakukan sebagai pemisah antar nomor/range.
    tokens = [
        x.strip()
        for x in re.split(r"[,;\s]+", normalized_text)
        if x.strip()
    ]

    pdf_pages = set()
    mapping_rows = []
    errors = []

    for token in tokens:
        kind, values = expand_page_token(token)

        if kind == "error":
            errors.append(values)
            continue

        for value in values:
            if kind == "roman":
                if value > roman_count:
                    errors.append(
                        f"{token}: halaman Romawi {int_to_roman(value).lower()} "
                        f"melebihi jumlah Romawi ({roman_count})."
                    )
                    continue

                pdf_page = value
                label = int_to_roman(value).lower()

            else:
                # Arabic starts after all Roman pages.
                pdf_page = roman_count + value
                label = str(value)

                max_arabic = max(0, total_pages - roman_count)
                if value < 1 or value > max_arabic:
                    errors.append(
                        f"{token}: halaman Arab {value} berada di luar "
                        f"rentang 1-{max_arabic}."
                    )
                    continue

            if pdf_page < 1 or pdf_page > total_pages:
                errors.append(
                    f"{token}: menghasilkan PDF halaman {pdf_page}, "
                    f"di luar rentang 1-{total_pages}."
                )
                continue

            pdf_pages.add(pdf_page)
            mapping_rows.append({
                "input": label,
                "jenis": "Romawi" if kind == "roman" else "Arab",
                "nomor": value,
                "pdf_page": pdf_page,
            })

    # Keep page order, not input order, so the split PDF follows
    # the original document sequence.
    sorted_pages = sorted(pdf_pages)

    # De-duplicate mapping display.
    unique_mapping = {}
    for row in mapping_rows:
        key = (row["jenis"], row["nomor"], row["pdf_page"])
        unique_mapping[key] = row

    mapping_rows = sorted(
        unique_mapping.values(),
        key=lambda x: x["pdf_page"]
    )

    return sorted_pages, mapping_rows, errors, tokens

def add_duplex_pairs(selected_pages, total_pages):
    result = set(selected_pages)
    for page in selected_pages:
        if page % 2 == 1:
            pair = page + 1
        else:
            pair = page - 1
        if 1 <= pair <= total_pages:
            result.add(pair)
    return sorted(result)


@st.cache_data(show_spinner="Menganalisis dan memisahkan PDF...")
def split_pdf_by_pages(file_bytes, selected_pages, total_pages):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    selected_set = set(selected_pages)

    doc_selected = fitz.open()
    doc_remaining = fitz.open()

    for page_num in range(total_pages):
        actual_page = page_num + 1
        if actual_page in selected_set:
            doc_selected.insert_pdf(
                doc, from_page=page_num, to_page=page_num
            )
        else:
            doc_remaining.insert_pdf(
                doc, from_page=page_num, to_page=page_num
            )

    pdf_selected = doc_selected.write() if len(doc_selected) else None
    pdf_remaining = doc_remaining.write() if len(doc_remaining) else None

    doc_selected.close()
    doc_remaining.close()
    doc.close()

    remaining_pages = [
        p for p in range(1, total_pages + 1) if p not in selected_set
    ]

    return (
        selected_pages,
        remaining_pages,
        pdf_selected,
        pdf_remaining,
    )


@st.cache_data(show_spinner="Menganalisis warna dan memisahkan PDF...")
def process_and_split_pdf(
    file_bytes, force_bw, sens, min_pct, mode, total_p
):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pure_color_pages = []

    if not force_bw:
        for page_num in range(total_p):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=72, colorspace=fitz.csRGB)
            samples = pix.samples
            n = pix.n

            total_pixels = pix.width * pix.height
            color_pixel_count = 0

            # Sampling setiap 2 pixel untuk menjaga performa.
            # Karena yang dihitung hanya sample, denominator juga
            # disesuaikan dengan jumlah sample.
            step = n * 2
            sample_count = 0

            for i in range(0, len(samples) - n + 1, step):
                r = samples[i]
                g = samples[i + 1]
                b = samples[i + 2]
                sample_count += 1

                if (
                    abs(r - g) > sens
                    or abs(r - b) > sens
                    or abs(g - b) > sens
                ):
                    color_pixel_count += 1

            if sample_count:
                color_ratio = (color_pixel_count / sample_count) * 100
            else:
                color_ratio = 0

            if color_ratio >= min_pct:
                pure_color_pages.append(page_num + 1)

    final_color_set = set(pure_color_pages)

    if mode == "Duplex (Bolak-balik)" and not force_bw:
        final_color_set = set(
            add_duplex_pairs(sorted(final_color_set), total_p)
        )

    final_color_list = sorted(final_color_set)
    final_bw_list = [
        p for p in range(1, total_p + 1)
        if p not in final_color_set
    ]

    doc_warna = fitz.open()
    doc_bw = fitz.open()

    for page_num in range(total_p):
        actual_page = page_num + 1
        if actual_page in final_color_set:
            doc_warna.insert_pdf(
                doc, from_page=page_num, to_page=page_num
            )
        else:
            doc_bw.insert_pdf(
                doc, from_page=page_num, to_page=page_num
            )

    pdf_warna_bytes = doc_warna.write() if len(doc_warna) else None
    pdf_bw_bytes = doc_bw.write() if len(doc_bw) else None

    doc_warna.close()
    doc_bw.close()
    doc.close()

    return (
        final_color_list,
        final_bw_list,
        pdf_warna_bytes,
        pdf_bw_bytes,
        pure_color_pages,
    )


def format_page_list(pages, max_chars=900):
    if not pages:
        return "—"

    text = ", ".join(map(str, pages))
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + " ..."


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
<div class="hero">
    <div class="hero-kicker">LITNUS PRINTING • PRODUCTION TOOL</div>
    <div class="hero-title">🖨️ PDF Splitter & Cost Calculator</div>
    <div class="hero-sub">
        Analisis halaman, pemisahan PDF, kalkulasi biaya produksi,
        diskon oplos, finishing, dan struk transaksi dalam satu aplikasi.
    </div>
    <div style="margin-top:12px;">
        <span class="pill">PDF SPLITTER</span>
        <span class="pill">MANUAL PAGE SELECTOR</span>
        <span class="pill">ROMAN + ARAB OFFSET</span>
        <span class="pill">AUTO COLOR DETECTION</span>
        <span class="pill">COST CALCULATOR</span>
        <span class="pill">DUPLEX AWARE</span>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR PRODUCTION SETTINGS
# ============================================================

st.sidebar.header("📦 Spesifikasi Produksi")

ukuran_buku = st.sidebar.selectbox(
    "Ukuran Buku",
    list(PRICING_MATRIX.keys()),
)

jenis_kertas = st.sidebar.selectbox(
    "Jenis Kertas Isi",
    ["HVS 70", "BP 57"],
)

mode_cetak = st.sidebar.selectbox(
    "Mode Cetak",
    ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"],
)

jenis_jilid = st.sidebar.selectbox(
    "Jenis Jilid",
    ["Soft Cover", "Hard Cover"],
)

st.sidebar.markdown("---")
st.sidebar.header("🔢 Volume Oplos")

jumlah_cetak = st.sidebar.number_input(
    "Jumlah Cetak (Eksemplar/Buku)",
    min_value=1,
    value=1,
    step=1,
)

base_warna = PRICING_MATRIX[ukuran_buku][jenis_kertas]["warna"]
base_bw = PRICING_MATRIX[ukuran_buku][jenis_kertas]["bw"]

if mode_cetak == "Simplex (Satu Sisi)":
    rate_warna = int(base_warna * 1.5)
    rate_bw = int(base_bw * 1.5)
else:
    rate_warna = base_warna
    rate_bw = base_bw

base_soft = PRICING_MATRIX[ukuran_buku]["base_finishing_soft"]

if jenis_jilid == "Hard Cover":
    rate_finishing_base = int(base_soft * 1.5)
else:
    rate_finishing_base = base_soft


# ============================================================
# INPUT MODE
# ============================================================

st.subheader("🛠️ Pilih Metode Analisis")

mode_input = st.radio(
    "Metode Analisis",
    [
        "Otomatis — Analisis Warna PDF",
        "Manual — Pilih Halaman & Split PDF",
        "Manual — Input Jumlah Halaman Saja",
    ],
    horizontal=True,
)

if mode_input == "Manual — Pilih Halaman & Split PDF":
    st.caption(
        "💡 Mode manual mendukung nomor Romawi dan Arab. "
        "Contoh: jika Romawi = 12, maka xii = PDF 12 sedangkan 8 = PDF 20."
    )

total_pages = 0
count_warna = 0
count_bw = 0
nama_file_asli = "Order_Manual_Litnus"

final_color_list = []
final_bw_list = []
pdf_warna_bytes = None
pdf_bw_bytes = None
ready_to_calculate = False

input_bytes = None


# ============================================================
# MODE 1 — AUTOMATIC COLOR ANALYSIS
# ============================================================

if mode_input == "Otomatis — Analisis Warna PDF":

    st.sidebar.markdown("---")
    st.sidebar.header("🎨 Parameter Deteksi Warna")

    force_bw_all = st.sidebar.checkbox(
        "Paksa SEMUA Halaman Menjadi BW",
        value=False,
    )

    sensitivitas = st.sidebar.slider(
        "Batas Kontras Warna",
        min_value=5,
        max_value=50,
        value=25,
        step=5,
    )

    min_color_percentage = st.sidebar.slider(
        "Batas Minimum Area Warna (%)",
        min_value=0.01,
        max_value=5.00,
        value=0.10,
        step=0.05,
    )

    uploaded_file = st.file_uploader(
        "Unggah File PDF Buku",
        type=["pdf"],
        key="auto_pdf",
    )

    if uploaded_file is not None:
        nama_file_asli = os.path.splitext(uploaded_file.name)[0]
        input_bytes = uploaded_file.getvalue()

        temp_doc = fitz.open(stream=input_bytes, filetype="pdf")
        total_pages = len(temp_doc)
        temp_doc.close()

        st.info(
            f"📄 {uploaded_file.name} • "
            f"{total_pages} halaman"
        )

        (
            final_color_list,
            final_bw_list,
            pdf_warna_bytes,
            pdf_bw_bytes,
            raw_color_pages,
        ) = process_and_split_pdf(
            input_bytes,
            force_bw_all,
            sensitivitas,
            min_color_percentage,
            mode_cetak,
            total_pages,
        )

        count_warna = len(final_color_list)
        count_bw = len(final_bw_list)
        ready_to_calculate = total_pages > 0

        if mode_cetak == "Duplex (Bolak-balik)" and raw_color_pages:
            if set(raw_color_pages) != set(final_color_list):
                st.success(
                    "🔄 Duplex aktif: halaman pasangan otomatis "
                    "ikut dimasukkan ke hasil warna."
                )


# ============================================================
# MODE 2 — MANUAL PAGE SELECTOR
# ============================================================

elif mode_input == "Manual — Pilih Halaman & Split PDF":

    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Manual Page Selector")

    roman_count = st.sidebar.number_input(
        "Jumlah Halaman Romawi",
        min_value=0,
        value=12,
        step=1,
        help=(
            "Jumlah halaman awal yang menggunakan nomor Romawi. "
            "Contoh: jika 12, maka xii = PDF 12 dan halaman Arab 8 = PDF 20."
        ),
    )

    auto_pair = st.sidebar.checkbox(
        "Cari halaman sebaliknya otomatis",
        value=True,
        disabled=(mode_cetak != "Duplex (Bolak-balik)"),
        help=(
            "Jika halaman PDF 7 dipilih, halaman PDF 8 akan ikut. "
            "Jika halaman PDF 8 dipilih, halaman PDF 7 akan ikut."
        ),
    )

    st.sidebar.caption(
        f"📘 Dengan {roman_count} halaman Romawi: "
        f"Arab 1 dimulai pada PDF halaman {roman_count + 1}."
    )

    uploaded_file = st.file_uploader(
        "Unggah File PDF Buku",
        type=["pdf"],
        key="manual_pdf",
    )

    if uploaded_file is not None:
        nama_file_asli = os.path.splitext(uploaded_file.name)[0]
        input_bytes = uploaded_file.getvalue()

        if (
            "manual_result" in st.session_state
            and st.session_state.manual_result.get("nama_file") != nama_file_asli
        ):
            del st.session_state.manual_result

        temp_doc = fitz.open(stream=input_bytes, filetype="pdf")
        total_pages = len(temp_doc)
        temp_doc.close()

        st.info(
            f"📄 {uploaded_file.name} • "
            f"{total_pages} halaman tersedia"
        )

        max_arabic_pages = max(0, total_pages - roman_count)

        st.markdown(
            f"""
<div class="glass-card">
    <div class="section-title">
        🎯 Tentukan Halaman yang Ingin Dipisahkan
    </div>
    <div style="font-size:13px;color:#8fa3b8;line-height:1.7;">
        Masukkan nomor halaman buku, bukan nomor urut PDF.
        <br>
        <b>Romawi:</b> i, iii, vii, xii
        &nbsp; • &nbsp;
        <b>Arab:</b> 1, 3, 8, 20
        <br>
        <b>Range:</b> iii-vii, 3-8
        <br>
        Dengan <b>{roman_count}</b> halaman Romawi:
        <b>xii → PDF {roman_count}</b> dan
        <b>8 → PDF {roman_count + 8}</b>.
        <br>
        Halaman Arab yang tersedia: <b>1-{max_arabic_pages}</b>.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        page_input = st.text_area(
            "Nomor halaman",
            placeholder=(
                "Contoh: iii, v, xii, 3, 8, 20\n"
                "atau: iii-vii, 3-8"
            ),
            height=95,
            key="manual_page_input",
        )

        (
            selected_input_pages,
            mapping_rows,
            parse_errors,
            parsed_tokens,
        ) = parse_page_input(
            page_input,
            total_pages,
            int(roman_count),
        )

        if parse_errors:
            st.warning(
                "⚠️ " + " • ".join(parse_errors)
            )

        if selected_input_pages:

            # Pair physical PDF pages for duplex.
            final_color_list = (
                add_duplex_pairs(
                    selected_input_pages,
                    total_pages,
                )
                if auto_pair
                else selected_input_pages
            )

            final_bw_list = [
                p for p in range(1, total_pages + 1)
                if p not in set(final_color_list)
            ]

            count_warna = len(final_color_list)
            count_bw = len(final_bw_list)

            # Physical pages added only because of duplex pairing.
            added_pairs = sorted(
                set(final_color_list)
                - set(selected_input_pages)
            )

            col_a, col_b, col_c = st.columns(3)

            col_a.metric(
                "Halaman Input",
                f"{len(selected_input_pages)} hlm",
            )

            col_b.metric(
                "Halaman Terpilih",
                f"{count_warna} hlm",
            )

            col_c.metric(
                "Halaman Sisa",
                f"{count_bw} hlm",
            )

            # Mapping preview
            st.markdown("### 🔎 Hasil Konversi Nomor Buku → Nomor PDF")

            mapping_html = """
<div class="glass-card" style="padding:12px 18px;">
<table style="width:100%;border-collapse:collapse;font-size:13px;">
<thead>
<tr>
<th style="padding:9px;text-align:left;">Input</th>
<th style="padding:9px;text-align:left;">Jenis</th>
<th style="padding:9px;text-align:left;">Nomor Buku</th>
<th style="padding:9px;text-align:right;">PDF Fisik</th>
</tr>
</thead>
<tbody>
"""

            for row in mapping_rows:
                mapping_html += f"""
<tr>
<td style="padding:8px 9px;"><b>{row["input"]}</b></td>
<td style="padding:8px 9px;">{row["jenis"]}</td>
<td style="padding:8px 9px;">{row["nomor"]}</td>
<td style="padding:8px 9px;text-align:right;color:#10b981;font-weight:800;">
    PDF {row["pdf_page"]}
</td>
</tr>
"""

            mapping_html += """
</tbody>
</table>
</div>
"""

            st.markdown(
                mapping_html,
                unsafe_allow_html=True,
            )

            if auto_pair and added_pairs:
                st.success(
                    "🔄 Halaman sebaliknya ditambahkan otomatis: "
                    + format_page_list(added_pairs)
                )

            c1, c2 = st.columns(2)

            with c1:
                st.markdown(
                    f"""
                    <div class="result-card result-color">
                        <div class="section-title">
                            🎯 PDF HALAMAN TERPILIH
                        </div>
                        <div class="page-list">
                            {format_page_list(final_color_list, 1800)}
                        </div>
                        <div style="margin-top:10px;color:#10b981;font-weight:800;">
                            {count_warna} halaman
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div class="result-card result-bw">
                        <div class="section-title">
                            ⚫ PDF HALAMAN SISANYA
                        </div>
                        <div class="page-list">
                            {format_page_list(final_bw_list, 1800)}
                        </div>
                        <div style="margin-top:10px;color:#60a5fa;font-weight:800;">
                            {count_bw} halaman
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button(
                "⚡ Proses & Pisahkan PDF",
                use_container_width=True,
                key="manual_split_button",
            ):
                (
                    final_color_list,
                    final_bw_list,
                    pdf_warna_bytes,
                    pdf_bw_bytes,
                ) = split_pdf_by_pages(
                    input_bytes,
                    tuple(final_color_list),
                    total_pages,
                )

                st.session_state.manual_result = {
                    "final_color_list": final_color_list,
                    "final_bw_list": final_bw_list,
                    "pdf_warna_bytes": pdf_warna_bytes,
                    "pdf_bw_bytes": pdf_bw_bytes,
                    "nama_file": nama_file_asli,
                }

                st.success(
                    "✅ PDF berhasil diproses dan dipisahkan."
                )

            # Ambil hasil dari session jika tombol sudah ditekan.
            if "manual_result" in st.session_state:
                result = st.session_state.manual_result
                if result["nama_file"] == nama_file_asli:
                    final_color_list = result["final_color_list"]
                    final_bw_list = result["final_bw_list"]
                    pdf_warna_bytes = result["pdf_warna_bytes"]
                    pdf_bw_bytes = result["pdf_bw_bytes"]

            ready_to_calculate = True

# ============================================================
# MODE 3 — MANUAL COUNT ONLY
# ============================================================

else:

    st.info(
        "💡 Mode manual sederhana: masukkan jumlah halaman "
        "Warna dan BW tanpa mengunggah PDF."
    )

    nama_file_asli = st.text_input(
        "Nama File / Judul Buku",
        value="Buku_Titipan_Customer",
    )

    col_in1, col_in2 = st.columns(2)

    with col_in1:
        count_warna = int(
            st.number_input(
                "Jumlah Halaman WARNA",
                min_value=0,
                value=0,
                step=1,
            )
        )

    with col_in2:
        count_bw = int(
            st.number_input(
                "Jumlah Halaman HITAM PUTIH (BW)",
                min_value=0,
                value=0,
                step=1,
            )
        )

    total_pages = count_warna + count_bw
    ready_to_calculate = total_pages > 0


# ============================================================
# CALCULATION ENGINE
# ============================================================

if ready_to_calculate:

    tz_wib = timezone(timedelta(hours=7))
    waktu_sekarang = datetime.now(tz_wib)

    str_tanggal = waktu_sekarang.strftime(
        "%d/%m/%Y %H:%M:%S WIB"
    )

    str_trx = waktu_sekarang.strftime(
        "TRX/%Y%m%d%H%M%S"
    )

    # --------------------------------------------------------
    # DISCOUNT PRINTING
    # --------------------------------------------------------

    diskon_isi_persen = 0
    tiers = [4, 10, 20, 30, 50, 100, 200, 500, 1000]

    for idx, tier in enumerate(tiers):
        if jumlah_cetak >= tier:
            diskon_isi_persen = (idx + 1) * 4

    diskon_isi_persen = min(diskon_isi_persen, 32)

    rate_warna_akhir = int(
        rate_warna * (1 - diskon_isi_persen / 100)
    )

    rate_bw_akhir = int(
        rate_bw * (1 - diskon_isi_persen / 100)
    )

    # --------------------------------------------------------
    # COST CONTENT
    # --------------------------------------------------------

    cost_warna_per_buku = count_warna * rate_warna_akhir
    cost_bw_per_buku = count_bw * rate_bw_akhir

    total_isi_per_buku = (
        cost_warna_per_buku + cost_bw_per_buku
    )

    # --------------------------------------------------------
    # FINISHING DISCOUNT
    # --------------------------------------------------------

    calc_oplos_finishing = min(
        jumlah_cetak,
        200,
    )

    persen_diskon_finishing = (
        calc_oplos_finishing // 5
    ) * 2

    persen_diskon_finishing = min(
        persen_diskon_finishing,
        40,
    )

    nilai_diskon_finishing_per_buku = int(
        rate_finishing_base
        * (persen_diskon_finishing / 100)
    )

    rate_finishing_akhir = (
        rate_finishing_base
        - nilai_diskon_finishing_per_buku
    )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_harga_per_eks = (
        total_isi_per_buku
        + rate_finishing_akhir
    )

    total_isi_all = (
        total_isi_per_buku
        * jumlah_cetak
    )

    total_finishing_all = (
        rate_finishing_akhir
        * jumlah_cetak
    )

    grand_total = (
        total_harga_per_eks
        * jumlah_cetak
    )

    nominal_dp = int(
        grand_total * 0.5
    )

    # --------------------------------------------------------
    # FULL COLOR COMPARISON
    # --------------------------------------------------------

    cost_full_warna_all = (
        total_pages
        * base_warna
        * jumlah_cetak
    ) + (
        rate_finishing_base
        * jumlah_cetak
    )

    hemat = (
        cost_full_warna_all
        - grand_total
    )

    # ========================================================
    # METRICS
    # ========================================================

    st.markdown("---")
    st.subheader("📊 Analisis Produksi")

    if count_warna > 0:
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        c1.metric(
            "🎨 Halaman Terpilih",
            f"{count_warna} hlm",
        )

        c2.metric(
            "⚫ Halaman Sisa",
            f"{count_bw} hlm",
        )

        c3.metric(
            "💰 Harga / Eks",
            format_rupiah(total_harga_per_eks),
        )

        c4.metric(
            "📦 Grand Total",
            format_rupiah(grand_total),
        )

        c5.metric(
            "🌈 Full Colour",
            format_rupiah(cost_full_warna_all),
        )

        c6.metric(
            "💚 Efisiensi",
            format_rupiah(hemat),
            delta="Hemat",
        )

    else:
        c1, c2, c3, c4, c5 = st.columns(5)

        c1.metric(
            "🎨 Halaman Terpilih",
            f"{count_warna} hlm",
        )

        c2.metric(
            "⚫ Halaman BW",
            f"{count_bw} hlm",
        )

        c3.metric(
            "💰 Harga / Eks",
            format_rupiah(total_harga_per_eks),
        )

        c4.metric(
            "📦 Grand Total",
            format_rupiah(grand_total),
        )

        c5.metric(
            "🌈 Full Colour",
            format_rupiah(cost_full_warna_all),
        )

    # ========================================================
    # COST SUMMARY
    # ========================================================

    st.markdown("### 💰 Ringkasan Biaya Produksi")

    table_html = f"""
    <div class="glass-card">
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr>
                <th style="padding:12px;text-align:left;">Komponen</th>
                <th style="padding:12px;text-align:left;">Detail</th>
                <th style="padding:12px;text-align:right;">Total</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="padding:11px;">Ukuran & Kertas</td>
                <td style="padding:11px;">{ukuran_buku} • {jenis_kertas} • {mode_cetak}</td>
                <td style="padding:11px;text-align:right;">—</td>
            </tr>
            <tr>
                <td style="padding:11px;">Jilid</td>
                <td style="padding:11px;">{jenis_jilid}</td>
                <td style="padding:11px;text-align:right;">{format_rupiah(rate_finishing_akhir)} / eks</td>
            </tr>
            <tr>
                <td style="padding:11px;">Cetak Isi × {jumlah_cetak} Eks</td>
                <td style="padding:11px;">Warna {count_warna} hlm + BW {count_bw} hlm • Diskon isi {diskon_isi_persen}%</td>
                <td style="padding:11px;text-align:right;">{format_rupiah(total_isi_all)}</td>
            </tr>
            <tr>
                <td style="padding:11px;">Finishing × {jumlah_cetak} Eks</td>
                <td style="padding:11px;">Diskon finishing {persen_diskon_finishing}%</td>
                <td style="padding:11px;text-align:right;">{format_rupiah(total_finishing_all)}</td>
            </tr>
            <tr style="background:rgba(16,185,129,.12);">
                <td style="padding:13px;font-weight:800;">GRAND TOTAL</td>
                <td style="padding:13px;font-weight:800;">{jumlah_cetak} eksemplar</td>
                <td style="padding:13px;text-align:right;font-weight:900;color:#10b981;">{format_rupiah(grand_total)}</td>
            </tr>
            <tr>
                <td style="padding:13px;font-weight:700;">DP 50%</td>
                <td style="padding:13px;">Minimum pembayaran awal</td>
                <td style="padding:13px;text-align:right;font-weight:800;">{format_rupiah(nominal_dp)}</td>
            </tr>
        </tbody>
    </table>
    </div>
    """

    st.markdown(
        table_html,
        unsafe_allow_html=True,
    )

    # ========================================================
    # PAGE DETAIL
    # ========================================================

    if mode_input != "Manual — Input Jumlah Halaman Saja":

        with st.expander("👁️ Lihat Rincian Nomor Halaman"):

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**🎨 Halaman Terpilih**")
                st.code(
                    format_page_list(
                        final_color_list,
                        4000,
                    ),
                    language="text",
                )

            with col2:
                st.markdown("**⚫ Halaman Sisa**")
                st.code(
                    format_page_list(
                        final_bw_list,
                        4000,
                    ),
                    language="text",
                )

    # ========================================================
    # RECEIPT
    # ========================================================

    def format_halaman_struk(lst):
        if not lst:
            return "[]"

        lines = []

        for i in range(0, len(lst), 15):
            lines.append(
                ", ".join(
                    map(str, lst[i:i + 15])
                )
            )

        return "[\n    " + ",\n    ".join(lines) + "\n]"

    struk_text = f"""
======================================================================
                         LITNUS PRINTING
                       STRUK PEMBAYARAN
======================================================================

Tanggal       : {str_tanggal}
No. Transaksi : {str_trx}
Nama File     : {nama_file_asli}
Total Halaman : {total_pages}
Ukuran Buku   : {ukuran_buku}
Bahan Kertas  : {jenis_kertas}
Jenis Jilid   : {jenis_jilid}
Mode Cetak    : {mode_cetak}
Jumlah Cetak  : {jumlah_cetak} eksemplar

----------------------------------------------------------------------
RINCIAN HALAMAN
----------------------------------------------------------------------

🎨 HALAMAN TERPILIH : {count_warna} halaman
"""

    if final_color_list:
        struk_text += (
            f"   Detail : {format_halaman_struk(final_color_list)}\n"
        )

    struk_text += (
        f"   Biaya  : {format_rupiah(cost_warna_per_buku)} / buku\n\n"
    )

    struk_text += (
        f"⚫ HALAMAN SISANYA : {count_bw} halaman\n"
    )

    if final_bw_list:
        struk_text += (
            f"   Detail : {format_halaman_struk(final_bw_list)}\n"
        )

    struk_text += f"""
   Biaya  : {format_rupiah(cost_bw_per_buku)} / buku

----------------------------------------------------------------------
RINCIAN AKUMULASI VOLUME
----------------------------------------------------------------------

TOTAL ISI PER EKS     : {format_rupiah(total_isi_per_buku)}
FINISHING PER EKS     : {format_rupiah(rate_finishing_akhir)}
TOTAL HARGA PER EKS   : {format_rupiah(total_harga_per_eks)}

{format_rupiah(total_harga_per_eks)} x {jumlah_cetak} Eks
= {format_rupiah(grand_total)}

----------------------------------------------------------------------
OPSI PEMBAYARAN
----------------------------------------------------------------------

[1] TOTAL LUNAS : {format_rupiah(grand_total)}
[2] DP 50%      : {format_rupiah(nominal_dp)}

Silahkan transfer sesuai pilihan pembayaran di atas.

Rekening:
• Mandiri : 144-00-2306065-7
  a/n PT Literasi Nusantara Abadi Grup

• BCA     : 117-737-3737
  a/n PT Literasi Nusantara Abadi Grup

Mohon kirimkan bukti transfer setelah pembayaran.

Terimakasih banyak.
Semoga diberi keberkahan dan kelancaran.

======================================================================
"""

    # ========================================================
    # DOWNLOAD AREA
    # ========================================================

    st.markdown("---")
    st.subheader("📄 File Siap Digunakan")

    if mode_input == "Otomatis — Analisis Warna PDF":
        downloads = [
            (
                "📥 Unduh Struk Analisis",
                struk_text,
                f"Struk_{nama_file_asli}.txt",
                "text/plain",
            )
        ]

        if pdf_warna_bytes:
            downloads.append(
                (
                    "🎨 Download PDF WARNA",
                    pdf_warna_bytes,
                    f"{nama_file_asli}_Mesin_WARNA.pdf",
                    "application/pdf",
                )
            )

        if pdf_bw_bytes:
            downloads.append(
                (
                    "⚫ Download PDF BW",
                    pdf_bw_bytes,
                    f"{nama_file_asli}_Mesin_BW.pdf",
                    "application/pdf",
                )
            )

    elif mode_input == "Manual — Pilih Halaman & Split PDF":

        downloads = [
            (
                "📥 Unduh Struk Analisis",
                struk_text,
                f"Struk_{nama_file_asli}.txt",
                "text/plain",
            )
        ]

        if pdf_warna_bytes:
            downloads.append(
                (
                    "🎯 Download PDF TERPILIH",
                    pdf_warna_bytes,
                    f"{nama_file_asli}_Terpilih.pdf",
                    "application/pdf",
                )
            )

        if pdf_bw_bytes:
            downloads.append(
                (
                    "⚫ Download PDF SISANYA",
                    pdf_bw_bytes,
                    f"{nama_file_asli}_Sisanya.pdf",
                    "application/pdf",
                )
            )

    else:
        downloads = [
            (
                "📥 Unduh Struk Analisis Manual",
                struk_text,
                f"Struk_Manual_{nama_file_asli}.txt",
                "text/plain",
            )
        ]

    cols = st.columns(len(downloads))

    for idx, (label, data, fname, mime) in enumerate(downloads):
        with cols[idx]:
            st.download_button(
                label=label,
                data=data,
                file_name=fname,
                mime=mime,
                use_container_width=True,
                key=f"download_{idx}_{mode_input}",
            )

    # ========================================================
    # RECEIPT PREVIEW
    # ========================================================

    with st.expander("🧾 Pratinjau Struk Kasir"):
        st.code(
            struk_text,
            language="text",
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
<div class="footer">
    Litnus Printing • PDF Splitter & Cost Calculator •
    Production Tool
</div>
""",
    unsafe_allow_html=True,
)
