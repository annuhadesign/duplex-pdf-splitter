import fitz  # PyMuPDF
import os
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Litnus Printing - PDF Splitter", layout="wide")

st.title("🖨️ Litnus Printing - Duplex-Aware PDF Splitter & Cost Calculator")
st.write(
    "Aplikasi produksi untuk memisahkan halaman Warna & BW dengan logika ikatan lembar fisik (Duplex) beserta cetak struk dinamis."
)

# --- SIDEBAR: PENGATURAN BIAYA & TOLERANSI ---
st.sidebar.header("⚙️ Pengaturan Mesin & Biaya")
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
rate_warna = st.sidebar.number_input("Tarif Klik Warna (Rp)", min_value=0, value=1000, step=50)
rate_bw = st.sidebar.number_input("Tarif Klik BW (Rp)", min_value=0, value=150, step=50)

st.sidebar.markdown("---")
st.sidebar.header("📦 Pengaturan Finishing & Oplos")
jumlah_cetak = st.sidebar.number_input("Jumlah Cetak (Eksemplar/Buku)", min_value=1, value=1, step=1)
rate_finishing_base = 20000  # Biaya dasar finishing per buku (Cover, Laminasi, Jilid, Wrapping)

st.sidebar.markdown("---")
st.sidebar.header("🚨 Mode Darurat (Jika Auto-Sensing Gagal)")
force_bw_all = st.sidebar.checkbox("Paksa SEMUA Halaman Menjadi BW", value=False)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Parameter Deteksi Otomatis")
sensitivitas = st.sidebar.slider("Batas Kontras Warna (Delta RGB/CMYK)", min_value=5, max_value=50, value=25, step=5)
min_color_percentage = st.sidebar.slider("Batas Minimum Area Warna (%)", min_value=0.01, max_value=5.00, value=0.10, step=0.05)


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


# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Unggah File PDF Buku", type=["pdf"])

if uploaded_file is not None:
    nama_file_asli = os.path.splitext(uploaded_file.name)[0]
    
    # Generate Waktu Terkini secara dinamis saat halaman me-render
    waktu_sekarang = datetime.now()
    str_tanggal = waktu_sekarang.strftime("%d/%m/%Y %H:%M:%S")
    str_trx = waktu_sekarang.strftime("TRX/%Y%m%d%H%M%S")
    
    input_bytes = uploaded_file.read()
    temp_doc = fitz.open(stream=input_bytes, filetype="pdf")
    total_pages = len(temp_doc)
    temp_doc.close()
    
    st.info(f"📄 File berhasil dimuat: {uploaded_file.name} | Total: {total_pages} Halaman")
    
    # Jalankan pemrosesan
    final_color_list, final_bw_list, pdf_warna_bytes, pdf_bw_bytes = process_and_split_pdf(
        input_bytes, force_bw_all, sensitivitas, min_color_percentage, mode_cetak, total_pages
    )
    
    # --- LOGIKA KALKULASI BIAYA & DISKON FINISHING ---
    # 1. Biaya Cetak Isi per Buku
    cost_warna_per_buku = len(final_color_list) * rate_warna
    cost_bw_per_buku = len(final_bw_list) * rate_bw
    total_isi_per_buku = cost_warna_per_buku + cost_bw_per_buku
    
    # 2. Perhitungan Diskon Kelipatan 5 (Max 40%)
    persen_diskon = (jumlah_cetak // 5) * 2
    if persen_diskon > 40:
        persen_diskon = 40
        
    # 3. Biaya Finishing Setelah Diskon
    nilai_diskon_finishing_per_buku = int(rate_finishing_base * (persen_diskon / 100))
    rate_finishing_akhir = rate_finishing_base - nilai_diskon_finishing_per_buku
    
    # 4. Akumulasi Total Keseluruhan (Isi + Finishing) dikali Jumlah Oplos
    total_isi_all = total_isi_per_buku * jumlah_cetak
    total_finishing_all = rate_finishing_akhir * jumlah_cetak
    grand_total = total_isi_all + total_finishing_all
    
    # Selisih Efisiensi vs Full Warna
    cost_full_warna_all = (total_pages * rate_warna * jumlah_cetak) + (rate_finishing_akhir * jumlah_cetak)
    hemat = cost_full_warna_all - grand_total
    
    # --- TAMPILAN ANALISIS & SIMULASI PROFIT ---
    st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Halaman Warna (Mesin 1)", f"{len(final_color_list)} hlm")
    with col2:
        st.metric("Total Halaman BW (Mesin 2)", f"{len(final_bw_list)} hlm")
    with col3:
        st.metric("Estimasi Efisiensi Oplos", f"Rp {hemat:,}", delta="Hemat vs Full Warna")
        
    st.markdown("### 💰 Ringkasan Biaya Produksi")
    st.table({
        "Komponen Biaya": [
            f"Cetak Isi (Warna & BW) x {jumlah_cetak} Eks", 
            f"Finishing Jilid (Cover, Lam, Wrapping) x {jumlah_cetak} Eks",
            "GRAND TOTAL (Harus Dibayar)"
        ],
        "Nilai Rupiah": [
            f"Rp {total_isi_all:,}", 
            f"Rp {total_finishing_all:,} (Diskon {persen_diskon}%)", 
            f"Rp {grand_total:,}"
        ]
    })
    
    with st.expander("👁️ Lihat Rincian Nomor Halaman"):
        st.write(f"🎨 **Halaman Warna ({len(final_color_list)} hlm):** {final_color_list}")
        st.write(f"⚫ **Halaman BW ({len(final_bw_list)} hlm):** {final_bw_list}")
        
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
Mode Cetak   : {mode_cetak}
Jumlah Cetak : {jumlah_cetak} eksemplar

----------------------------------------------------------------------
RINCIAN HARGA (PER BUKU):
----------------------------------------------------------------------

🎨 WARNA ({len(final_color_list)} halaman)
   Halaman: {format_halaman_list(final_color_list)}
   Biaya   : Rp {cost_warna_per_buku:,} (Rp {rate_warna:,}/hal)

⚫ HITAM PUTIH ({len(final_bw_list)} halaman)
   Halaman: {format_halaman_list(final_bw_list)}
   Biaya   : Rp {cost_bw_per_buku:,} (Rp {rate_bw:,}/hal)

🟡 BW + FOOTER WARNA (0 halaman) [+20%]
   Halaman: []
   Biaya   : Rp 0 (Rp {int(rate_bw * 1.2):,}/hal)

----------------------------------------------------------------------
RINCIAN FINISHING & VOLUME:
----------------------------------------------------------------------
🛠️ BIAYA FINISHING HARDCOVER (Per Buku)
   (Cover, Laminasi, Jilid, Wrapping)
   Biaya Dasar : Rp {rate_finishing_base:,}
   Diskon Oplos: {persen_diskon}% (Kelipatan 5 eks, Maks 40%)
   Biaya Akhir : Rp {rate_finishing_akhir:,}

📊 TOTAL AKUMULASI ({jumlah_cetak} Eks)
   Total Cetak Isi : Rp {total_isi_all:,}
   Total Finishing : Rp {total_finishing_all:,}

----------------------------------------------------------------------
💰 TOTAL BAYAR: Rp {grand_total:,}
----------------------------------------------------------------------

Harga Dasar per Lembar:
   • Hitam Putih : Rp {rate_bw:,}
   • Warna       : Rp {rate_warna:,}

----------------------------------------------------------------------
Terima kasih atas kunjungan Anda!
~ Barang yang sudah dibeli tidak dapat ditukar ~
----------------------------------------------------------------------

*Struk ini sebagai bukti pembayaran yang sah
*Detail halaman terlampir untuk transparansi perhitungan
"""

    # --- BLOCK EKSPOR & UNDUH ---
    st.subheader("📄 Struk & Pemisah File Siap Cetak")
    
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
            
    st.markdown("---")
    st.markdown("### 📝 Pratinjau Struk Kasir")
    st.code(struk_text, language="text")
