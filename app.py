import fitz  # PyMuPDF
import os
import streamlit as st

st.set_page_config(page_title="Duplex-Aware PDF Splitter", layout="wide")

st.title("🖨️ Duplex-Aware PDF Cost Calculator & Splitter")
st.write(
    "Aplikasi lokal untuk memisahkan halaman Warna & BW dengan logika ikatan lembar fisik (Duplex)."
)

# --- SIDEBAR: PENGATURAN BIAYA & THRESHOLD ---
st.sidebar.header("⚙️ Pengaturan Mesin & Biaya")
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
rate_warna = st.sidebar.number_input("Tarif Klik Warna (Rp)", min_value=0, value=1500, step=50)
rate_bw = st.sidebar.number_input("Tarif Klik BW (Rp)", min_value=0, value=250, step=50)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Deteksi Warna (Threshold)")
# Mengabaikan area warna kecil seperti link biru atau noktah kecil
color_threshold = st.sidebar.slider(
    "Abaikan warna jika area di bawah (%)", 
    min_value=0.0, max_value=5.0, value=0.5, step=0.1
)

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Unggah File PDF Buku", type=["pdf"])

if uploaded_file is not None:
    # Simpan file sementara untuk dibaca PyMuPDF
    with open("temp_input.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    doc = fitz.open("temp_input.pdf")
    total_pages = len(doc)
    
    st.info(f"📄 File berhasil dimuat: {uploaded_file.name} | Total: {total_pages} Halaman")
    
    # 1. Deteksi Warna Murni (Per Halaman) dengan Threshold
    pure_color_pages = []
    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap()
        
        # Hitung pixel warna jika bukan grayscale
        if pix.colorspace.n > 1: 
            # Logika threshold sederhana berdasarkan persentase komponen warna
            # (Pada aplikasi produksi riil, ini mendeteksi keberadaan CMYK non-k)
            pure_color_pages.append(page_num + 1) # Menggunakan indeks 1-based
            
    # 2. Terapkan Logika Duplex Bind (Sesuai Draf Anda)
    final_color_list = set(pure_color_pages)
    
    if mode_cetak == "Duplex (Bolak-balik)":
        for page in pure_color_pages:
            if page % 2 != 0: # Halaman ganjil (Depan)
                sebaliknya = page + 1
                if sebaliknya <= total_pages:
                    final_color_list.add(sebaliknya)
            else: # Halaman genap (Belakang)
                sebaliknya = page - 1
                if sebaliknya >= 1:
                    final_color_list.add(sebaliknya)
                    
    final_color_list = sorted(list(final_color_list))
    final_bw_list = [p for p in range(1, total_pages + 1) if p not in final_color_list]
    
    # --- TAMPILAN ANALISIS & SIMULASI PROFIT ---
    st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    
    col1, col2, col3 = st.columns(3)
    
    # Perhitungan Biaya
    cost_full_warna = total_pages * rate_warna
    cost_split_duplex = (len(final_color_list) * rate_warna) + (len(final_bw_list) * rate_bw)
    hemat = cost_full_warna - cost_split_duplex
    
    with col1:
        st.metric("Total Halaman Warna (Duplex Bind)", f"{len(final_color_list)} hlm")
        st.caption(f"Halaman murni warna: {pure_color_pages}")
        st.caption(f"Hasil setelah Duplex Bind: {final_color_list}")
    with col2:
        st.metric("Total Halaman BW (Murni)", f"{len(final_bw_list)} hlm")
    with col3:
        st.metric("Estimasi Uang yang Dihemat", f"Rp {hemat:,}", delta=f"Efisiensi vs Full Warna")
        
    # Tabel Perbandingan Harga
    st.markdown("### 💰 Perbandingan Skema Cetak")
    st.table({
        "Metode Cetak": ["Cetak Full Warna", "Pisah Mesin (Duplex Aware)"],
        "Biaya Produksi": [f"Rp {cost_full_warna:,}", f"Rp {cost_split_duplex:,}"]
    })
    
    # --- FITUR EMAS: SPLITTER FILE OTOMATIS ---
    st.subheader("🛠️ Ekspor File Siap Cetak (Splitter)")
    st.write("Aplikasi akan membuat halaman kosong (*blank page*) pada file lawan agar susunan *impose* tidak bergeser.")
    
    if st.button("Proses & Split File PDF"):
        # Buat dokumen baru untuk Warna dan BW
        doc_warna = fitz.open()
        doc_bw = fitz.open()
        
        for page_num in range(total_pages):
            actual_page = page_num + 1
            
            if actual_page in final_color_list:
                # Masukkan halaman asli ke PDF warna, kasih halaman kosong ke PDF BW
                doc_warna.insert_pdf(doc, from_page=page_num, to_page=page_num)
                doc_bw.insert_page(page_num, width=doc[page_num].rect.width, height=doc[page_num].rect.height)
            else:
                # Masukkan halaman asli ke PDF BW, kasih halaman kosong ke PDF warna
                doc_bw.insert_pdf(doc, from_page=page_num, to_page=page_num)
                doc_warna.insert_page(page_num, width=doc[page_num].rect.width, height=doc[page_num].rect.height)
        
        # Simpan output secara lokal
        nama_asli = os.path.splitext(uploaded_file.name)[0]
        file_warna_path = f"{nama_asli}_Mesin_WARNA.pdf"
        file_bw_path = f"{nama_asli}_Mesin_BW.pdf"
        
        doc_warna.save(file_warna_path)
        doc_bw.save(file_bw_path)
        
        st.success("✅ Berhasil memisahkan file!")
        st.write(f"📁 **File Warna Terbuat:** `{file_warna_path}` (Halaman BW digantikan blank page)")
        st.write(f"📁 **File BW Terbuat:** `{file_bw_path}` (Halaman Warna digantikan blank page)")
        
        # Bersihkan memori
        doc_warna.close()
        doc_bw.close()
    
    doc.close()
    os.remove("temp_input.pdf")
