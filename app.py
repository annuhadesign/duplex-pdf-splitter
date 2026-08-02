import fitz  # PyMuPDF
import os
import streamlit as st

st.set_page_config(page_title="Duplex-Aware PDF Splitter", layout="wide")

st.title("🖨️ Duplex-Aware PDF Cost Calculator & Splitter")
st.write(
    "Aplikasi lokal untuk memisahkan halaman Warna & BW dengan logika ikatan lembar fisik (Duplex)."
)

# --- SIDEBAR: PENGATURAN BIAYA & TOLERANSI ---
st.sidebar.header("⚙️ Pengaturan Mesin & Biaya")
mode_cetak = st.sidebar.selectbox("Mode Cetak", ["Duplex (Bolak-balik)", "Simplex (Satu Sisi)"])
rate_warna = st.sidebar.number_input("Tarif Klik Warna (Rp)", min_value=0, value=1000, step=50)
rate_bw = st.sidebar.number_input("Tarif Klik BW (Rp)", min_value=0, value=150, step=50)

st.sidebar.markdown("---")
st.sidebar.header("🚨 Mode Darurat (Jika Auto-Sensing Gagal)")
force_bw_all = st.sidebar.checkbox("Paksa SEMUA Halaman Menjadi BW", value=False)
st.sidebar.caption("Centang ini jika file hitam-putih Anda terus-menerus terdeteksi sebagai warna oleh sistem.")

st.sidebar.markdown("---")
st.sidebar.header("🎯 Parameter Deteksi Otomatis")
sensitivitas = st.sidebar.slider("Batas Kontras Warna (Delta RGB/CMYK)", min_value=5, max_value=50, value=30, step=5)
min_color_percentage = st.sidebar.slider("Batas Minimum Area Warna (%)", min_value=0.01, max_value=5.00, value=0.50, step=0.05)

# --- UPLOAD FILE ---
uploaded_file = st.file_uploader("Unggah File PDF Buku", type=["pdf"])

if uploaded_file is not None:
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
                for i in range(0, len(samples), n * 2): # Lompat per 2 piksel biar cepat
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
        # Jika tombol darurat dicentang, halaman murni warna dikosongkan (semua dianggap BW)
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
    
    # --- TAMPILAN ANALISIS & SIMULASI PROFIT ---
    st.subheader("📊 Analisis Halaman & Kalkulator Selisih Profit")
    
    col1, col2, col3 = st.columns(3)
    
    cost_full_warna = total_pages * rate_warna
    cost_split_duplex = (len(final_color_list) * rate_warna) + (len(final_bw_list) * rate_bw)
    hemat = cost_full_warna - cost_split_duplex
    
    with col1:
        st.metric("Total Halaman Warna (Duplex Bind)", f"{len(final_color_list)} hlm")
    with col2:
        st.metric("Total Halaman BW (Murni)", f"{len(final_bw_list)} hlm")
    with col3:
        st.metric("Estimasi Uang yang Dihemat", f"Rp {hemat:,}", delta=f"Efisiensi vs Full Warna")
        
    st.markdown("### 💰 Perbandingan Skema Cetak")
    st.table({
        "Metode Cetak": ["Cetak Full Warna", "Pisah Mesin (Duplex Aware)"],
        "Biaya Produksi": [f"Rp {cost_full_warna:,}", f"Rp {cost_split_duplex:,}"]
    })
    
    # --- FITUR SPLITTER FILE ---
    st.subheader("🛠️ Ekspor File Siap Cetak (Splitter)")
    
    if st.button("Proses & Split File PDF"):
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
        
        nama_asli = os.path.splitext(uploaded_file.name)[0]
        file_warna_path = f"{nama_asli}_Mesin_WARNA.pdf"
        file_bw_path = f"{nama_asli}_Mesin_BW.pdf"
        
        doc_warna.save(file_warna_path)
        doc_bw.save(file_bw_path)
        
        st.success("✅ Berhasil memisahkan file!")
        st.write(f"📁 **File Warna:** `{file_warna_path}`")
        st.write(f"📁 **File BW:** `{file_bw_path}`")
        
        doc_warna.close()
        doc_bw.close()
    
    doc.close()
    os.remove("temp_input.pdf")
