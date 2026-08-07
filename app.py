import fitz  # PyMuPDF
import os
import streamlit as st
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Litnus Printing - PDF Splitter", layout="wide")

# --- INISIALISASI STATE TEMA ---
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

def toggle_theme():
    if st.session_state.theme_mode == "dark":
        st.session_state.theme_mode = "light"
    else:
        st.session_state.theme_mode = "dark"

# --- DEFINISI CSS TEMA ---
CSS_DARK_MODE = """
<style>
    .stApp {
        background-color: #0a0d14;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 90% 30%, rgba(59, 130, 246, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 50% 80%, rgba(139, 92, 246, 0.12) 0%, transparent 50%);
        background-attachment: fixed;
        color: #e2e8f0;
    }
    h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
    
    /* Paksa warna header tabel menjadi putih */
    [data-testid="stMarkdown"] table thead th { color: #ffffff !important; }

    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.5) !important;
        backdrop-filter: blur(20px) saturate(180%);
    }
    
    div[data-testid="stMetric"] {
        background: rgba(20, 27, 45, 0.6) !important;
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
    }
    
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; }
    
    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #022c22 !important;
    }
    
    button[title="Toggle Theme"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important;
        z-index: 9999999 !important; width: 60px !important; height: 60px !important;
        border-radius: 50% !important; background: rgba(30, 41, 59, 0.9) !important;
    }
</style>
"""

CSS_LIGHT_MODE = """
<style>
    .stApp {
        background-color: #f1f5f9;
        color: #1e293b;
    }
    h1, h2, h3 { color: #0f172a !important; }
    
    /* Paksa warna header tabel menjadi putih */
    [data-testid="stMarkdown"] table thead th { color: #ffffff !important; }

    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f09433 0%, #e6683c 30%, #dc2743 60%, #bc1888 100%) !important;
        border-radius: 20px !important;
        padding: 20px !important;
    }
    div[data-testid="stMetric"] *, div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {
        color: #ffffff !important; font-weight: 700 !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%) !important;
        color: #ffffff !important;
    }
    
    button[title="Toggle Theme"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important;
        z-index: 9999999 !important; width: 60px !important; height: 60px !important;
        border-radius: 50% !important; background: rgba(255, 255, 255, 0.95) !important;
    }
</style>
"""

# --- RENDER TEMA ---
if st.session_state.theme_mode == "dark":
    st.markdown(CSS_DARK_MODE, unsafe_allow_html=True)
    ikon_tema = "☀️" 
else:
    st.markdown(CSS_LIGHT_MODE, unsafe_allow_html=True)
    ikon_tema = "🌙"

st.button(ikon_tema, on_click=toggle_theme, help="Toggle Theme")

# --- HEADER & DATABASE ---
st.title("🖨️ Litnus Printing - PDF Splitter & Cost Calculator")
PRICING_MATRIX = {
    "A5 (14.8 x 21 cm)": {"base_finishing_soft": 25000, "HVS 70": {"warna": 500, "bw": 150}, "BP 57": {"warna": 550, "bw": 180}},
    "Unesco (15.5 x 23 cm)": {"base_finishing_soft": 27000, "HVS 70": {"warna": 600, "bw": 160}, "BP 57": {"warna": 650, "bw": 200}},
    "B5 ISO (17.6 x 25 cm)": {"base_finishing_soft": 30000, "HVS 70": {"warna": 800, "bw": 180}, "BP 57": {"warna": 850, "bw": 210}},
    "B5 JIS (18.2 x 25.7 cm)": {"base_finishing_soft": 31000, "HVS 70": {"warna": 900, "bw": 190}, "BP 57": {"warna": 950, "bw": 220}},
    "A4 (21 x 29.7 cm)": {"base_finishing_soft": 31000, "HVS 70": {"warna": 1000, "bw": 200}, "BP 57": {"warna": 1100, "bw": 250}}
}

# --- SIDEBAR ---
st.sidebar.header("📦 Spesifikasi")
ukuran_buku = st.sidebar.selectbox("Ukuran Buku", list(PRICING_MATRIX.keys()))
jenis_kertas = st.sidebar.selectbox("Jenis Kertas", ["HVS 70", "BP 57"])
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
jenis_jilid = st.sidebar.selectbox("Jenis Jilid", ["Soft Cover", "Hard Cover"])
jumlah_cetak = st.sidebar.number_input("Jumlah Cetak (Eksemplar)", min_value=1, value=1)

base_warna = PRICING_MATRIX[ukuran_buku][jenis_kertas]["warna"]
base_bw = PRICING_MATRIX[ukuran_buku][jenis_kertas]["bw"]
rate_warna = int(base_warna * 1.5) if mode_cetak == "Simplex (Satu Sisi)" else base_warna
rate_bw = int(base_bw * 1.5) if mode_cetak == "Simplex (Satu Sisi)" else base_bw
base_soft = PRICING_MATRIX[ukuran_buku]["base_finishing_soft"]
rate_finishing_base = int(base_soft * 1.5) if jenis_jilid == "Hard Cover" else base_soft

# --- FUNGSI PDF ---
@st.cache_data(show_spinner="Memproses...")
def process_and_split_pdf(file_bytes, mode, total_p):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pure_color_pages = []
    for page_num in range(total_p):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=72)
        samples = pix.samples
        if any(abs(samples[i] - samples[i+1]) > 20 or abs(samples[i] - samples[i+2]) > 20 for i in range(0, len(samples), pix.n)):
            pure_color_pages.append(page_num + 1)
    
    final_color_set = set(pure_color_pages)
    if mode == "Duplex (Bolak-balik)":
        for page in pure_color_pages:
            final_color_set.add(page + 1 if page % 2 != 0 else page - 1)
    
    final_color_list = sorted([p for p in final_color_set if 1 <= p <= total_p])
    final_bw_list = [p for p in range(1, total_p + 1) if p not in final_color_list]
    
    doc_warna = fitz.open()
    doc_bw = fitz.open()
    for page_num in range(total_p):
        if (page_num + 1) in final_color_list: doc_warna.insert_pdf(doc, from_page=page_num, to_page=page_num)
        else: doc_bw.insert_pdf(doc, from_page=page_num, to_page=page_num)
    
    return final_color_list, final_bw_list, doc_warna.write(), doc_bw.write()

# --- INPUT & LOGIC ---
mode_input = st.radio("Metode:", ["Otomatis (Upload PDF)", "Manual"], horizontal=True)
if mode_input == "Otomatis (Upload PDF)":
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
    if uploaded_file:
        input_bytes = uploaded_file.read()
        doc = fitz.open(stream=input_bytes, filetype="pdf")
        total_pages = len(doc)
        doc.close()
        final_color_list, final_bw_list, pdf_warna, pdf_bw = process_and_split_pdf(input_bytes, mode_cetak, total_pages)
        count_warna, count_bw = len(final_color_list), len(final_bw_list)
else:
    count_warna = st.number_input("Halaman Warna", 0)
    count_bw = st.number_input("Halaman BW", 0)
    total_pages = count_warna + count_bw

if total_pages > 0:
    # Perhitungan
    diskon_isi = 0
    for tier in [4, 10, 20, 30, 50, 100, 200, 500, 1000]:
        if jumlah_cetak >= tier: diskon_isi += 4
    
    rate_warna_akhir = int(rate_warna * (1 - min(diskon_isi, 32) / 100))
    rate_bw_akhir = int(rate_bw * (1 - min(diskon_isi, 32) / 100))
    total_isi_per_buku = (count_warna * rate_warna_akhir) + (count_bw * rate_bw_akhir)
    
    persen_finishing = min((min(jumlah_cetak, 200) // 5) * 2, 40)
    rate_finishing_akhir = rate_finishing_base - int(rate_finishing_base * (persen_finishing / 100))
    
    total_harga_per_eks = total_isi_per_buku + rate_finishing_akhir
    grand_total = total_harga_per_eks * jumlah_cetak
    
    # Tampilan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Warna", f"{count_warna} hlm")
    c2.metric("BW", f"{count_bw} hlm")
    c3.metric("Harga/Eks", f"Rp {total_harga_per_eks:,}")
    c4.metric("Grand Total", f"Rp {grand_total:,}")
    
    # Tabel HTML
    table_html = f"""
    <table style="width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 15px; overflow: hidden; border: 1px solid rgba(128,128,128,0.2);">
        <thead>
            <tr style="background: linear-gradient(135deg, #f09433 0%, #e6683c 30%, #dc2743 60%, #bc1888 100%);">
                <th style="padding: 12px 15px; text-align: left; font-weight: 700; font-size: 16px;">Spesifikasi Buku & Komponen</th>
                <th style="padding: 12px 15px; text-align: left; font-weight: 700; font-size: 16px;">Detail Perhitungan</th>
            </tr>
        </thead>
        <tbody style="background: {'rgba(30, 41, 59, 0.5)' if st.session_state.theme_mode == 'dark' else 'rgba(255, 255, 255, 0.8)'};">
            <tr><td style="padding: 10px 12px;">Ukuran & Kertas</td><td style="padding: 10px 12px;">{ukuran_buku} | {jenis_kertas}</td></tr>
            <tr><td style="padding: 10px 12px;">Jilid</td><td style="padding: 10px 12px;">{jenis_jilid}</td></tr>
            <tr><td style="padding: 10px 12px;">Total Harga (Lunas)</td><td style="padding: 10px 12px; font-weight: 700; color: #10b981;">Rp {grand_total:,}</td></tr>
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
