import fitz  # PyMuPDF
import os
import streamlit as st
from datetime import datetime

st.set_page_config(page_title="Litnus Printing - PDF Splitter", layout="wide")

st.title("🖨️ Litnus Printing - Duplex-Aware PDF Splitter & Cost Calculator")
st.write(
    "Aplikasi produksi untuk memisahkan halaman Warna & BW dengan logika ikatan lembar fisik (Duplex) beserta cetak struk."
)

# --- SIDEBAR: PENGATURAN BIAYA & TOLERANSI ---
st.sidebar.header("⚙️ Pengaturan Mesin & Biaya")
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
rate_warna = st.sidebar.number_input("Tarif Klik Warna (Rp)", min_value=0, value=1000, step=50)
rate_bw = st.sidebar.number_input("Tarif Klik BW (Rp)", min_value=0, value=150, step=50)

st.sidebar.markdown("---")
st.sidebar.header("🚨 Mode Darurat (Jika Auto-Sensing Gagal)")
force_bw_all = st.sidebar.checkbox("Paksa SEMUA Halaman Menjadi BW", value=False)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Parameter Deteksi Otomatis")
sensitivitas = st.sidebar.slider("Batas Kontras Warna (Delta RGB/CMYK)", min_value=5, max_value=50, value=25, step=5)
min_color_percentage = st.sidebar.slider("Batas Minimum Area Warna (%)", min_value=0.01, max_value=5.00, value=0.10, step=0.05)

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Unggah File PDF Buku", type=["pdf"])

if uploaded_file is not None:
    nama_file_asli = os.path.splitext(uploaded_file.name)[0]
    waktu_sekarang = datetime.now()
    str_tanggal = waktu_sekarang.strftime("%d/%m/%Y %H:%M:%S")
    str_trx = waktu_sekarang.strftime("TRX/%Y%m%d%H%M%S")
    
    with open("temp_input.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    doc = fitz.open("temp_input.pdf")
    total_pages = len(doc)
    
    st.info(f"📄 File berhasil dimuat: {uploaded_file.name} | Total: {total_pages} Halaman")
    
    pure_color_pages = []
    
    if not force_bw_all:
        progress_bar = st.progress(0)
        for page_num in range(total_pages):
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
                    if abs(r - g) > sensitivitas or abs(r - b) > sensitivitas or abs(g - b) > sensitivitas:
                        color_pixel_count += 1
                        
            elif n == 4:  # CMYK
                for i in range(0, len(samples), n * 2):
                    c = samples[i]
                    m = samples[i+1]
                    y = samples[i+2]
                    if c > sensitivitas or m > sensitivitas or y > sensitivitas:
                        color_pixel_count += 1
            
            color_ratio = (color_pixel_count / total_pixels) * 100
            if color_ratio >= min_color_percentage:
                pure_color_pages.append(page_num + 1)
                
            progress_bar.progress((page_num + 1) / total_pages)
        progress_bar.empty()
    else:
        pure_color_pages = []
            
    # 2. Terapkan Logika Duplex Bind
    final_color_list = set(pure_color_pages)
    
    if mode_cetak == "Duplex (Bolak-balik)" and not force_bw_all:
        for page in pure_color_pages:
            if page % 2 != 0: 
                sebaliknya = page + 1
                if sebaliknya <= total_pages:
                    final_color_list.add(sebaliknya)
            else: 
                sebaliknya = page - 1
                if sebaliknya >= 1:
                    final_color_list.add(sebaliknya)
                    
    final_color_list = sorted(list(final_color_list))
    final_bw_list = [p for p in range(1, total_pages + 1) if p not in final_color_list]
    
    # Hitung Biaya
    cost_full_warna = total_pages * rate_warna
    cost_warna_total = len(final_color_list) * rate_warna
    cost_bw_total = len(final_bw_list) * rate_bw
    cost_split_duplex = cost_warna_total + cost_bw_total
    hemat = cost_full_warna - cost_split_duplex
    
    # --- TAMPILAN ANALISIS & SIMULASI PROFIT ---
    st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Halaman Warna (Mesin 1)", f"{len(final_color_list)} hlm")
    with col2:
        st.metric("Total Halaman BW (Mesin 2)", f"{len(final_bw_list)} hlm")
    with col3:
        st.metric("Estimasi Uang yang Dihemat", f"Rp {hemat:,}", delta=f"Efisiensi vs Full Warna")
        
    st.markdown("### 💰 Perbandingan Skema Cetak")
    st.table({
        "Metode Cetak": ["Cetak Full Warna", "Pisah Mesin (Duplex Aware)"],
        "Biaya Produksi": [f"Rp {cost_full_warna:,}", f"Rp {cost_split_duplex:,}"]
    })
    
    with st.expander("👁️ Lihat Rincian Halaman Warna & BW"):
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

----------------------------------------------------------------------
RINCIAN HARGA:
----------------------------------------------------------------------

🎨 WARNA ({len(final_color_list)} halaman)
   Halaman: {format_halaman_list(final_color_list)}
   Biaya   : Rp {cost_warna_total:,} (Rp {rate_warna:,}/hal)

⚫ HITAM PUTIH ({len(final_bw_list)} halaman)
   Halaman: {format_halaman_list(final_bw_list)}
   Biaya   : Rp {cost_bw_total:,} (Rp {rate_bw:,}/hal)

🟡 BW + FOOTER WARNA (0 halaman) [+20%]
   Halaman: []
   Biaya   : Rp 0 (Rp {int(rate_bw * 1.2):,}/hal)

----------------------------------------------------------------------
💰 TOTAL BAYAR: Rp {cost_split_duplex:,}
----------------------------------------------------------------------

Harga per Lembar:
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
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        st.download_button(
            label="📥 Unduh Struk Analisis (.txt)",
            data=struk_text,
            file_name=f"Struk_{nama_file_asli}.txt",
            mime="text/plain"
        )
        
    with col_btn2:
        # Proses Splitter langsung dilakukan otomatis saat file di-upload agar user bisa langsung unduh
        doc_warna = fitz.open()
        doc_bw = fitz.open()
        
        for page_num in range(total_pages):
            actual_page = page_num + 1
            if actual_page in final_color_list:
                doc_warna.insert_pdf(doc, from_page=page_num, to_page=page_num)
                doc_bw.insert_page(page_num, width=doc[page_num].rect.width, height=doc[page_num].rect.height)
            else:
                doc_bw.insert_pdf(doc, from_page=page_num, to_page=page_num)
                doc_warna.insert_page(page_num, width=doc[page_num].rect.width, height=doc[page_num].rect.height)
        
        # Konversi ke biner memori agar bisa didownload langsung di web cloud
        pdf_warna_bytes = doc_warna.write()
        pdf_bw_bytes = doc_bw.write()
        
        doc_warna.close()
        doc_bw.close()

        st.write("🎉 **File Pemisah PDF Siap Diunduh:**")
        
        # Tombol download file WARNA
        st.download_button(
            label="🎨 Download PDF Khusus Mesin WARNA",
            data=pdf_warna_bytes,
            file_name=f"{nama_file_asli}_Mesin_WARNA.pdf",
            mime="application/pdf"
        )
        
        # Tombol download file BW
        st.download_button(
            label="⚫ Download PDF Khusus Mesin BW",
            data=pdf_bw_bytes,
            file_name=f"{nama_file_asli}_Mesin_BW.pdf",
            mime="application/pdf"
        )
            
    st.markdown("---")
    st.markdown("### 📝 Pratinjau Struk Kasir")
    st.code(struk_text, language="text")
    
    doc.close()
    os.remove("temp_input.pdf")
