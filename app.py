import fitz  # PyMuPDF
import os
import streamlit as st
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Litnus Printing - PDF Splitter", layout="wide")

# --- DEFINISI CSS TEMA 1: DARK EMERALD GLASS ---
CSS_TEMA_1 = """
<style>
    /* Latar Belakang Gelap dengan Ambient Radial Glow */
    .stApp {
        background-color: #0a0d14;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(16, 185, 129, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 90% 30%, rgba(59, 130, 246, 0.18) 0%, transparent 45%),
            radial-gradient(circle at 50% 80%, rgba(139, 92, 246, 0.12) 0%, transparent 50%);
        background-attachment: fixed;
        color: #e2e8f0;
    }

    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.5) !important;
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    div[data-testid="stMetric"] {
        background: rgba(20, 27, 45, 0.6) !important;
        backdrop-filter: blur(16px) saturate(180%);
        -webkit-backdrop-filter: blur(16px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5) !important;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        box-shadow: 0 12px 35px -5px rgba(16, 185, 129, 0.15) !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
    }

    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stNumberInput input,
    div[data-testid="stFileUploader"] {
        background: rgba(30, 41, 59, 0.5) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        color: #f8fafc !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #022c22 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3) !important;
        transition: all 0.25s ease !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
        box-shadow: 0 6px 25px rgba(16, 185, 129, 0.5) !important;
        transform: translateY(-2px) !important;
        color: #022c22 !important;
    }

    .stDownloadButton > button {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
        font-weight: 600 !important;
        transition: all 0.25s ease !important;
    }

    .stDownloadButton > button:hover {
        background: rgba(255, 255, 255, 0.12) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        color: #34d399 !important;
    }

    pre, code {
        background: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        color: #38bdf8 !important;
    }

    div[data-testid="stTable"], div[data-testid="stExpander"] {
        background: rgba(20, 27, 45, 0.4) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
    }
</style>
"""

# --- DEFINISI CSS TEMA 2: VIBRANT LIQUID GLASS ---
CSS_TEMA_2 = """
<style>
    /* Background Liquid Organic Gradient */
    .stApp {
        background-color: #0c021a;
        background-image: 
            radial-gradient(circle at 10% 25%, rgba(0, 183, 255, 0.55) 0%, transparent 45%),
            radial-gradient(circle at 38% 18%, rgba(157, 0, 255, 0.6) 0%, transparent 50%),
            radial-gradient(circle at 85% 75%, rgba(255, 0, 166, 0.55) 0%, transparent 55%),
            radial-gradient(circle at 25% 85%, rgba(140, 40, 255, 0.4) 0%, transparent 45%);
        background-attachment: fixed;
        color: #f8fafc;
    }

    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
    }

    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(28px) saturate(210%);
        -webkit-backdrop-filter: blur(28px) saturate(210%);
        border-right: 1px solid rgba(255, 255, 255, 0.18) !important;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(25px) saturate(200%);
        -webkit-backdrop-filter: blur(25px) saturate(200%);
        border: 1px solid rgba(255, 255, 255, 0.22) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.35) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        background: rgba(255, 255, 255, 0.14) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 16px 48px 0 rgba(236, 72, 153, 0.25) !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #e2e8f0 !important;
        font-size: 0.85rem !important;
        font-weight: 500;
    }

    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 800 !important;
        text-shadow: 0 0 12px rgba(56, 189, 248, 0.4);
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stNumberInput input,
    div[data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 14px !important;
        color: #ffffff !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #f43f5e 0%, #d946ef 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 14px !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 25px rgba(217, 70, 239, 0.45) !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #fb7185 0%, #e879f9 100%) !important;
        box-shadow: 0 8px 30px rgba(217, 70, 239, 0.7) !important;
        transform: translateY(-2px) !important;
    }

    .stDownloadButton > button {
        background: rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 14px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }

    .stDownloadButton > button:hover {
        background: rgba(255, 255, 255, 0.18) !important;
        border-color: rgba(244, 114, 182, 0.5) !important;
        color: #f472b6 !important;
    }

    pre, code {
        background: rgba(10, 2, 22, 0.75) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 16px !important;
        color: #38bdf8 !important;
    }

    div[data-testid="stTable"], div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.06) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 16px !important;
    }
</style>
"""

# --- HEADER LAYOUT & SWITCH TEMA DI KANAN ATAS ---
col_header, col_switch = st.columns([3.2, 1.2])

with col_switch:
    pilihan_tema = st.selectbox(
        "🎨 Pilih Tema Tampilan",
        ["Tema 1: Dark Emerald Glass", "Tema 2: Vibrant Liquid Glass"],
        index=0,
        key="theme_switch"
    )

if pilihan_tema == "Tema 1: Dark Emerald Glass":
    st.markdown(CSS_TEMA_1, unsafe_allow_html=True)
else:
    st.markdown(CSS_TEMA_2, unsafe_allow_html=True)

with col_header:
    st.title("🖨️ Litnus Printing - PDF Splitter & Cost Calculator")
    st.write(
        "Aplikasi produksi otomatis untuk memisahkan halaman Warna & BW berdasarkan Ukuran Buku dan Jenis Kertas beserta cetak struk dinamis."
    )

# --- DATABASE RUMUS HARGA ---
PRICING_MATRIX = {
    "A5 (14.8 x 21 cm)": {
        "base_finishing_soft": 25000,
        "HVS 70": {"warna": 500, "bw": 150},
        "BP 57": {"warna": 550, "bw": 180}
    },
    "Unesco (15.5 x 23 cm)": {
        "base_finishing_soft": 27000,
        "HVS 70": {"warna": 600, "bw": 160},
        "BP 57": {"warna": 650, "bw": 200}
    },
    "B5 ISO (17.6 x 25 cm)": {
        "base_finishing_soft": 30000,
        "HVS 70": {"warna": 800, "bw": 180},
        "BP 57": {"warna": 850, "bw": 210}
    },
    "B5 JIS (18.2 x 25.7 cm)": {
        "base_finishing_soft": 31000,
        "HVS 70": {"warna": 900, "bw": 190},
        "BP 57": {"warna": 950, "bw": 220}
    },
    "A4 (21 x 29.7 cm)": {
        "base_finishing_soft": 31000,
        "HVS 70": {"warna": 1000, "bw": 200},
        "BP 57": {"warna": 1100, "bw": 250}
    }
}

# --- SIDEBAR: PENGATURAN PRODUKSI ---
st.sidebar.header("📦 Spesifikasi Buku & Cetak")
ukuran_buku = st.sidebar.selectbox("Ukuran Buku", list(PRICING_MATRIX.keys()))
jenis_kertas = st.sidebar.selectbox("Jenis Kertas Isi", ["HVS 70", "BP 57"])
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
jenis_jilid = st.sidebar.selectbox("Jenis Jilid", ["Soft Cover", "Hard Cover"])

st.sidebar.markdown("---")
st.sidebar.header("🔢 Volume Oplos")
jumlah_cetak = st.sidebar.number_input("Jumlah Cetak (Eksemplar/Buku)", min_value=1, value=1, step=1)

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


# --- FUNGSI PROSES PDF DENGAN CACHE ---
@st.cache_data(show_spinner="Memproses pemisahan halaman PDF...")
def process_and_split_pdf(file_bytes, force_bw, sens, min_pct, mode, total_p):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pure_color_pages = []
    
    if not force_bw:
        for page_num in range(total_p):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=72)
            samples = pix.samples
            n = pix.n
            
            total_pixels = pix.width * pix.height
            color_pixel_count = 0
            
            if n == 3:  # RGB
                for i in range(0, len(samples), n * 2): 
                    r = samples[i]
                    g = samples[i+1]
                    b = samples[i+2]
                    if abs(r - g) > sens or abs(r - b) > sens or abs(g - b) > sens:
                        color_pixel_count += 1
                        
            elif n == 4:  # CMYK
                for i in range(0, len(samples), n * 2):
                    c = samples[i]
                    m = samples[i+1]
                    y = samples[i+2]
                    if c > sens or m > sens or y > sens:
                        color_pixel_count += 1
            
            color_ratio = (color_pixel_count / total_pixels) * 100
            if color_ratio >= min_pct:
                pure_color_pages.append(page_num + 1)
    
    final_color_set = set(pure_color_pages)
    if mode == "Duplex (Bolak-balik)" and not force_bw:
        for page in pure_color_pages:
            if page % 2 != 0: 
                sebaliknya = page + 1
                if sebaliknya <= total_p:
                    final_color_set.add(sebaliknya)
            else: 
                sebaliknya = page - 1
                if sebaliknya >= 1:
                    final_color_set.add(sebaliknya)
                    
    final_color_list = sorted(list(final_color_set))
    final_bw_list = [p for p in range(1, total_p + 1) if p not in final_color_list]
    
    doc_warna = fitz.open()
    doc_bw = fitz.open()
    
    for page_num in range(total_p):
        actual_page = page_num + 1
        if actual_page in final_color_list:
            doc_warna.insert_pdf(doc, from_page=page_num, to_page=page_num)
        else:
            doc_bw.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
    pdf_warna_bytes = doc_warna.write()
    pdf_bw_bytes = doc_bw.write()
    
    doc_warna.close()
    doc_bw.close()
    doc.close()
    
    return final_color_list, final_bw_list, pdf_warna_bytes, pdf_bw_bytes


# --- PILIHAN MODE INPUT ---
st.subheader("🛠️ Pilih Metode Input Data")
mode_input = st.radio("Metode Analisis:", ["Otomatis (Upload PDF & Split File)", "Manual (Input Jumlah Halaman Saja)"], horizontal=True)

total_pages = 0
count_warna = 0
count_bw = 0
nama_file_asli = "Order_Manual_Litnus"
final_color_list = []
final_bw_list = []
pdf_warna_bytes = None
pdf_bw_bytes = None
ready_to_calculate = False

if mode_input == "Otomatis (Upload PDF & Split File)":
    st.sidebar.markdown("---")
    st.sidebar.header("🚨 Mode Darurat & Parameter")
    force_bw_all = st.sidebar.checkbox("Paksa SEMUA Halaman Menjadi BW", value=False)
    sensitivitas = st.sidebar.slider("Batas Kontras Warna", min_value=5, max_value=50, value=25, step=5)
    min_color_percentage = st.sidebar.slider("Batas Minimum Area Warna (%)", min_value=0.01, max_value=5.00, value=0.10, step=0.05)
    
    uploaded_file = st.file_uploader("Unggah File PDF Buku", type=["pdf"])
    
    if uploaded_file is not None:
        nama_file_asli = os.path.splitext(uploaded_file.name)[0]
        input_bytes = uploaded_file.read()
        
        temp_doc = fitz.open(stream=input_bytes, filetype="pdf")
        total_pages = len(temp_doc)
        temp_doc.close()
        
        st.info(f"📄 File berhasil dimuat: {uploaded_file.name} | Total: {total_pages} Halaman")
        
        final_color_list, final_bw_list, pdf_warna_bytes, pdf_bw_bytes = process_and_split_pdf(
            input_bytes, force_bw_all, sensitivitas, min_color_percentage, mode_cetak, total_pages
        )
        count_warna = len(final_color_list)
        count_bw = len(final_bw_list)
        ready_to_calculate = True

else:
    st.info("💡 Mode Manual Aktif: Masukkan jumlah halaman secara langsung di bawah.")
    nama_file_asli = st.text_input("Nama File / Judul Buku", value="Buku_Titipan_Customer")
    
    col_in1, col_in2 = st.columns(2)
    with col_in1:
        count_warna = st.number_input("Jumlah Halaman WARNA", min_value=0, value=0, step=1)
    with col_in2:
        count_bw = st.number_input("Jumlah Halaman HITAM PUTIH (BW)", min_value=0, value=0, step=1)
        
    total_pages = count_warna + count_bw
    ready_to_calculate = total_pages > 0


# --- BLOK PROSES KALKULASI UTAMA ---
if ready_to_calculate:
    tz_wib = timezone(timedelta(hours=7))
    waktu_sekarang = datetime.now(tz_wib)
    str_tanggal = waktu_sekarang.strftime("%d/%m/%Y %H:%M:%S WIB")
    str_trx = waktu_sekarang.strftime("TRX/%Y%m%d%H%M%S")
    
    # 1. Logika Diskon Kelipatan 4% Berdasarkan Oplos Cetak Isi
    diskon_isi_persen = 0
    tiers = [4, 10, 20, 30, 50, 100, 200, 500, 1000]
    for idx, tier in enumerate(tiers):
        if jumlah_cetak >= tier:
            diskon_isi_persen = (idx + 1) * 4
            
    if diskon_isi_persen > 32:
        diskon_isi_persen = 32
    
    rate_warna_akhir = int(rate_warna * (1 - diskon_isi_persen / 100))
    rate_bw_akhir = int(rate_bw * (1 - diskon_isi_persen / 100))
    
    cost_warna_per_buku = count_warna * rate_warna_akhir
    cost_bw_per_buku = count_bw * rate_bw_akhir
    total_isi_per_buku = cost_warna_per_buku + cost_bw_per_buku
    
    # 2. Perhitungan Diskon Finishing Oplos
    calc_oplos_finishing = min(jumlah_cetak, 200)
    persen_diskon_finishing = (calc_oplos_finishing // 5) * 2
    if persen_diskon_finishing > 40:
        persen_diskon_finishing = 40
        
    # 3. Biaya Finishing Setelah Diskon
    nilai_diskon_finishing_per_buku = int(rate_finishing_base * (persen_diskon_finishing / 100))
    rate_finishing_akhir = rate_finishing_base - nilai_diskon_finishing_per_buku
    
    # --- RINGKASAN PER EKSEMPLAR ---
    total_harga_per_eks = total_isi_per_buku + rate_finishing_akhir
    
    # 4. Akumulasi Total Keseluruhan & DP 50%
    total_isi_all = total_isi_per_buku * jumlah_cetak
    total_finishing_all = rate_finishing_akhir * jumlah_cetak
    grand_total = total_harga_per_eks * jumlah_cetak
    nominal_dp = int(grand_total * 0.5)
    
    # Selisih Efisiensi vs Full Warna Standard
    cost_full_warna_all = (total_pages * base_warna * jumlah_cetak) + (rate_finishing_base * jumlah_cetak)
    hemat = cost_full_warna_all - grand_total
    
    # --- TAMPILAN ANALISIS & METRIK ---
    st.markdown("---")
    st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    
    # LOGIKA CONDITIONAL METRICS:
    # Jika BUKU CAMPURAN (Ada Halaman Warna DAN Ada Halaman BW) -> 6 Kolom Komparasi Efisiensi
    if count_warna > 0 and count_bw > 0:
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("Total Halaman Warna", f"{count_warna} hlm")
        with col2:
            st.metric("Total Halaman BW", f"{count_bw} hlm")
        with col3:
            st.metric("Total Harga Per Eks", f"Rp {total_harga_per_eks:,}")
        with col4:
            st.metric("GRAND TOTAL (Oplos)", f"Rp {grand_total:,}")
        with col5:
            st.metric("Grand Total Full Colour", f"Rp {cost_full_warna_all:,}")
        with col6:
            st.metric("Estimasi Efisiensi Oplos", f"Rp {hemat:,}", delta="Hemat vs Full Warna")

    # Jika HANYA WARNA saja ATAU HANYA BW saja -> 4 Kolom Standar
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Halaman Warna", f"{count_warna} hlm")
        with col2:
            st.metric("Total Halaman BW", f"{count_bw} hlm")
        with col3:
            st.metric("Total Harga Per Eks", f"Rp {total_harga_per_eks:,}")
        with col4:
            st.metric("GRAND TOTAL", f"Rp {grand_total:,}")
        
    st.markdown("### 💰 Ringkasan Biaya Produksi")
    st.table({
        "Spesifikasi Buku & Komponen": [
            f"Ukuran & Bahan Kertas Isi",
            f"Jilid Cover Buku",
            f"Cetak Isi (Warna & BW) x {jumlah_cetak} Eks", 
            f"Finishing Jilid x {jumlah_cetak} Eks",
            "PILIHAN 1: GRAND TOTAL (Lunas)",
            "PILIHAN 2: NOMINAL UANG MUKA (DP 50%)"
        ],
        "Detail Perhitungan": [
            f"{ukuran_buku} | Kertas {jenis_kertas} ({mode_cetak})",
            f"{jenis_jilid}",
            f"Rp {total_isi_all:,} (Diskon Isi {diskon_isi_persen}%)", 
            f"Rp {total_finishing_all:,} (Diskon Finishing {persen_diskon_finishing}%)", 
            f"Rp {grand_total:,}",
            f"Rp {nominal_dp:,}"
        ]
    })
    
    if mode_input == "Otomatis (Upload PDF & Split File)":
        with st.expander("👁️ Lihat Rincian Nomor Halaman"):
            st.write(f"🎨 **Halaman Warna ({count_warna} hlm):** {final_color_list}")
            st.write(f"⚫ **Halaman BW ({count_bw} hlm):** {final_bw_list}")
            
    # --- GENERATE STRUK TEXT ---
    def format_halaman_list(lst):
        if not lst:
            return "[]"
        lines = []
        for i in range(0, len(lst), 15):
            lines.append(", ".join(map(str, lst[i:i+15])))
        return "[\n    " + ",\n    ".join(lines) + "\n   ]"

    struk_text = f"""======================================================================
                    LITNUS PRINTING
                    Struk Pembayaran
======================================================================

Tanggal      : {str_tanggal}
No. Transaksi: {str_trx}
Nama File    : {nama_file_asli}
Total Halaman: {total_pages}
Ukuran Buku  : {ukuran_buku}
Bahan Kertas : {jenis_kertas}
Jenis Jilid  : {jenis_jilid}
Mode Cetak   : {mode_cetak}
Jumlah Cetak : {jumlah_cetak} eksemplar

----------------------------------------------------------------------
RINCIAN HARGA (PER BUKU - SETELAH DISKON OPLOS & PENYESUAIAN MODE):
----------------------------------------------------------------------

🎨 WARNA ({count_warna} halaman)"""

    if mode_input == "Otomatis (Upload PDF & Split File)":
        text_detail_warna = format_halaman_list(final_color_list)
        struk_text += f"\n   Detail  : {text_detail_warna}"
        
    struk_text += f"\n   Biaya   : Rp {cost_warna_per_buku:,}\n\n⚫ HITAM PUTIH ({count_bw} halaman)"

    if mode_input == "Otomatis (Upload PDF & Split File)":
        text_detail_bw = format_halaman_list(final_bw_list)
        struk_text += f"\n   Detail  : {text_detail_bw}"
        
    struk_text += f"""
   Biaya   : Rp {cost_bw_per_buku:,}

----------------------------------------------------------------------
RINCIAN AKUMULASI VOLUME PRODUKSI:
----------------------------------------------------------------------
📝 TOTAL ISI PER EKS : Rp {total_isi_per_buku:,}
🛠️ FINISHING PER EKS : Rp {rate_finishing_akhir:,} ({jenis_jilid.upper()})
💵 TOTAL HARGA PER EKS: Rp {total_harga_per_eks:,} (Isi + Finishing)

📊 PERKALIAN TOTAL VOLUME:
   Rp {total_harga_per_eks:,} x {jumlah_cetak} Eks = Rp {grand_total:,}

----------------------------------------------------------------------
💰 OPSI PILIHAN PEMBAYARAN:
----------------------------------------------------------------------
 [1] TOTAL LUNAS : Rp {grand_total:,}
 [2] NOMINAL DP   : Rp {nominal_dp:,} (50% dari total biaya)
----------------------------------------------------------------------

Sebelum Kami proses, silahkan Transfer senilai total biaya di atas 
atau DP minimal 50% dulu agar orderan diproses. 

Berikut detail rekening kami:
• Mandiri : 144-00-2306065-7 a/n PT Literasi Nusantara Abadi Grup
• BCA     : 117-737-3737     a/n PT Literasi Nusantara Abadi Grup

Dan mohon kirimkan bukti otentik setelah transfer.

Terimakasih banyak, semoga diberi keberkahan dan kelancaran 
dalam hidup.
----------------------------------------------------------------------
"""

    # --- BLOCK EKSPOR & UNDUH ---
    st.subheader("📄 Struk & Pemisah File Siap Cetak")
    
    if mode_input == "Otomatis (Upload PDF & Split File)":
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            st.download_button(
                label="📥 Unduh Struk Analisis (.txt)",
                data=struk_text,
                file_name=f"Struk_{nama_file_asli}.txt",
                mime="text/plain",
                key="btn_txt"
            )
        with col_btn2:
            st.download_button(
                label="🎨 Download PDF Mesin WARNA",
                data=pdf_warna_bytes,
                file_name=f"{nama_file_asli}_Mesin_WARNA.pdf",
                mime="application/pdf",
                key="btn_pdf_warna"
            )
        with col_btn3:
            st.download_button(
                label="⚫ Download PDF Mesin BW",
                data=pdf_bw_bytes,
                file_name=f"{nama_file_asli}_Mesin_BW.pdf",
                mime="application/pdf",
                key="btn_pdf_bw"
            )
    else:
        st.download_button(
            label="📥 Unduh Struk Analisis Manual (.txt)",
            data=struk_text,
            file_name=f"Struk_Manual_{nama_file_asli}.txt",
            mime="text/plain",
            key="btn_txt_manual"
        )
            
    st.markdown("---")
    st.markdown("### 📝 Pratinjau Struk Kasir")
    st.code(struk_text, language="text")

# --- FOOTER HALAMAN ---
st.markdown("---")
footer_color = "#10b981" if pilihan_tema == "Tema 1: Dark Emerald Glass" else "#f43f5e"
footer_html = f"""
    <div style="text-align: center; color: rgba(255,255,255,0.6); font-size: 14px; padding: 10px 0px;">
        <p>Copyright © <a href="https://www.instagram.com/annuha_zarkasyi/?hl=id" target="_blank" style="color: {footer_color}; text-decoration: none; font-weight: bold;">@annuhazarkasyi</a></p>
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
