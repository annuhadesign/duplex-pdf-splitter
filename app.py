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

# --- DEFINISI CSS TEMA 1: DARK EMERALD GLASS (DARK MODE) ---
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
    
    section[data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.5) !important;
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    div[data-testid="stMetric"] {
        background: rgba(20, 27, 45, 0.6) !important;
        backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5) !important;
    }
    
    div[data-testid="stMetric"] *,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricDelta"] {
        font-weight: 700 !important;
    }
    
    div[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
    div[data-testid="stMetricValue"] { color: #38bdf8 !important; }
    
    .stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: #022c22 !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3) !important;
    }
    
    /* Tombol Tema (Floating) */
    button[title="Toggle Theme"] {
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        z-index: 999999 !important;
        width: 50px !important;
        height: 50px !important;
        border-radius: 50% !important;
        background: rgba(30, 41, 59, 0.8) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        font-size: 24px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5) !important;
        padding: 0 !important;
        transition: transform 0.2s ease !important;
    }
    button[title="Toggle Theme"]:hover { transform: scale(1.1); border-color: #10b981 !important; }
    
    div[data-testid="stTable"] { background: rgba(20, 27, 45, 0.4) !important; border-radius: 14px !important; }
</style>
"""

# --- DEFINISI CSS TEMA 2: FROSTED-GLASS PASTEL (LIGHT MODE) ---
CSS_LIGHT_MODE = """
<style>
    /* Latar Belakang Gradien Pastel Lembut & Kontras */
    .stApp {
        background-color: #f1f5f9;
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(186, 230, 253, 0.7) 0%, transparent 40%),
            radial-gradient(circle at 90% 20%, rgba(254, 205, 211, 0.7) 0%, transparent 40%),
            radial-gradient(circle at 50% 90%, rgba(221, 214, 254, 0.7) 0%, transparent 50%);
        background-attachment: fixed;
        color: #1e293b;
    }

    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    p, span, label { color: #475569; font-weight: 500; }

    section[data-testid="stSidebar"] {
        background: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border-right: 1px solid rgba(255, 255, 255, 0.9) !important;
    }

    /* Kartu Metrik dengan Gradien Warna Logo Instagram & Memaksa Semua Teks Menjadi Putih Tebal */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #f09433 0%, #e6683c 30%, #dc2743 60%, #bc1888 100%) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 10px 25px rgba(220, 39, 67, 0.25) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 30px rgba(220, 39, 67, 0.35) !important;
    }
    
    /* Memaksa seluruh elemen teks/angka/label di dalam kartu metrik menjadi putih bersih dan bold */
    div[data-testid="stMetric"] *,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricDelta"],
    div[data-testid="stMetric"] div,
    div[data-testid="stMetric"] span,
    div[data-testid="stMetric"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stNumberInput input,
    div[data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid rgba(226, 232, 240, 0.9) !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        backdrop-filter: blur(10px);
    }

    /* Tombol Utama Gradien Magenta/Ungu */
    .stButton > button {
        background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 12px 24px !important;
        box-shadow: 0 8px 25px rgba(236, 72, 153, 0.3) !important;
    }
    .stButton > button:hover {
        box-shadow: 0 10px 30px rgba(236, 72, 153, 0.45) !important;
        transform: translateY(-2px) !important;
    }

    /* Tombol Tema (Floating) */
    button[title="Toggle Theme"] {
        position: fixed !important;
        top: 20px !important;
        right: 20px !important;
        z-index: 999999 !important;
        width: 50px !important;
        height: 50px !important;
        border-radius: 50% !important;
        background: rgba(255, 255, 255, 0.9) !important;
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(255, 255, 255, 1) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.08) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 24px !important;
        padding: 0 !important;
        transition: transform 0.2s ease !important;
    }
    button[title="Toggle Theme"]:hover { transform: scale(1.1); }
    
    div[data-testid="stTable"] { background: rgba(255, 255, 255, 0.8) !important; backdrop-filter: blur(15px); border-radius: 16px !important; box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid rgba(255,255,255,0.9); }
    th { color: #64748b !important; }
    td { color: #334155 !important; }
</style>
"""

# --- RENDER TEMA & TOMBOL FLOATING ---
if st.session_state.theme_mode == "dark":
    st.markdown(CSS_DARK_MODE, unsafe_allow_html=True)
    ikon_tema = "☀️" 
else:
    st.markdown(CSS_LIGHT_MODE, unsafe_allow_html=True)
    ikon_tema = "🌙"

st.button(ikon_tema, on_click=toggle_theme, help="Toggle Theme")

# --- HEADER LAYOUT UTAMA ---
st.title("🖨️ Litnus Printing - PDF Splitter & Cost Calculator")
st.write("Aplikasi produksi otomatis untuk memisahkan halaman Warna & BW berdasarkan Ukuran Buku dan Jenis Kertas beserta cetak struk dinamis.")

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
        count_warna = int(st.number_input("Jumlah Halaman WARNA", min_value=0, value=0, step=1))
    with col_in2:
        count_bw = int(st.number_input("Jumlah Halaman HITAM PUTIH (BW)", min_value=0, value=0, step=1))
        
    total_pages = count_warna + count_bw
    ready_to_calculate = total_pages > 0


# --- BLOK PROSES KALKULASI UTAMA ---
if ready_to_calculate:
    tz_wib = timezone(timedelta(hours=7))
    waktu_sekarang = datetime.now(tz_wib)
    str_tanggal = waktu_sekarang.strftime("%d/%m/%Y %H:%M:%S WIB")
    str_trx = waktu_sekarang.strftime("TRX/%Y%m%d%H%M%S")
    
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
    
    calc_oplos_finishing = min(jumlah_cetak, 200)
    persen_diskon_finishing = (calc_oplos_finishing // 5) * 2
    if persen_diskon_finishing > 40:
        persen_diskon_finishing = 40
        
    nilai_diskon_finishing_per_buku = int(rate_finishing_base * (persen_diskon_finishing / 100))
    rate_finishing_akhir = rate_finishing_base - nilai_diskon_finishing_per_buku
    
    total_harga_per_eks = total_isi_per_buku + rate_finishing_akhir
    total_isi_all = total_isi_per_buku * jumlah_cetak
    total_finishing_all = rate_finishing_akhir * jumlah_cetak
    grand_total = total_harga_per_eks * jumlah_cetak
    nominal_dp = int(grand_total * 0.5)
    
    cost_full_warna_all = (total_pages * base_warna * jumlah_cetak) + (rate_finishing_base * jumlah_cetak)
    hemat = cost_full_warna_all - grand_total
    
    
    # =====================================================================
    # --- RENDER CONTAINER ANALISIS DENGAN GRADASI INSTAGRAM (LIGHT MODE) ---
    # =====================================================================
    st.markdown("---")
    if st.session_state.theme_mode == "light":
        st.markdown("""
        <div style="background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); padding: 18px 24px; border-radius: 18px; box-shadow: 0 10px 30px rgba(220, 39, 67, 0.3); margin-bottom: 20px;">
            <div style="color: #ffffff !important; font-weight: 700 !important; margin: 0; font-size: 1.25rem;">📊 Analisis Halaman & Kalkulator Selisih Profit</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    
    # KONDISI 1: JIKA BUKU CAMPURAN (Warna diisi & BW diisi)
    if (count_warna > 0) and (count_bw > 0):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Total Halaman Warna", f"{count_warna} hlm")
        c2.metric("Total Halaman BW", f"{count_bw} hlm")
        c3.metric("TOTAL HARGA PER EKS", f"Rp {total_harga_per_eks:,}")
        c4.metric("GRAND TOTAL (Oplos)", f"Rp {grand_total:,}")
        c5.metric("Grand Total Full Colour", f"Rp {cost_full_warna_all:,}")
        c6.metric("Estimasi Efisiensi Oplos", f"Rp {hemat:,}", delta="Hemat vs Full Warna")

    # KONDISI 2: JIKA BUKU FULL WARNA atau FULL BW SAJA
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Halaman Warna", f"{count_warna} hlm")
        c2.metric("Total Halaman BW", f"{count_bw} hlm")
        c3.metric("TOTAL HARGA PER EKS", f"Rp {total_harga_per_eks:,}")
        c4.metric("GRAND TOTAL", f"Rp {grand_total:,}") 
    # =====================================================================


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
        if not lst: return "[]"
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
                label="📥 Unduh Struk Analisis",
                data=struk_text,
                file_name=f"Struk_{nama_file_asli}.txt",
                mime="text/plain"
            )
        with col_btn2:
            st.download_button(
                label="🎨 Download PDF WARNA",
                data=pdf_warna_bytes,
                file_name=f"{nama_file_asli}_Mesin_WARNA.pdf",
                mime="application/pdf"
            )
        with col_btn3:
            st.download_button(
                label="⚫ Download PDF BW",
                data=pdf_bw_bytes,
                file_name=f"{nama_file_asli}_Mesin_BW.pdf",
                mime="application/pdf"
            )
    else:
        st.download_button(
            label="📥 Unduh Struk Analisis Manual",
            data=struk_text,
            file_name=f"Struk_Manual_{nama_file_asli}.txt",
            mime="text/plain"
        )
            
    st.markdown("---")
    st.markdown("### 📝 Pratinjau Struk Kasir")
    st.code(struk_text, language="text")

# --- FOOTER HALAMAN ---
st.markdown("---")
footer_color = "#10b981" if st.session_state.theme_mode == "dark" else "#ec4899"
footer_html = f"""
    <div style="text-align: center; color: rgba(148, 163, 184, 0.8); font-size: 14px; padding: 10px 0px;">
        <p>Copyright © <a href="https://www.instagram.com/annuha_zarkasyi/?hl=id" target="_blank" style="color: {footer_color}; text-decoration: none; font-weight: bold;">@annuhazarkasyi</a></p>
    </div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
