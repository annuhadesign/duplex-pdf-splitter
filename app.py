import fitz  # PyMuPDF
import os
import streamlit as st
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Litnus Printing - PDF Splitter", layout="wide")

# --- INISIALISASI STATE TEMA ---
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

def toggle_theme():
    st.session_state.theme_mode = "light" if st.session_state.theme_mode == "dark" else "dark"

# --- CSS GLOBAL ---
CSS_DARK_MODE = """
<style>
    .stApp { background-color: #0a0d14; color: #e2e8f0; }
    h1, h2, h3 { color: #ffffff !important; font-weight: 700 !important; }
    
    /* Floating Button */
    button[title="Toggle Theme"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important;
        z-index: 9999999 !important; width: 60px !important; height: 60px !important;
        border-radius: 50% !important; background: rgba(30, 41, 59, 0.9) !important;
        backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.15) !important;
        font-size: 26px !important; box-shadow: 0 8px 25px rgba(0,0,0,0.6) !important;
    }
</style>
"""

CSS_LIGHT_MODE = """
<style>
    .stApp { background-color: #f1f5f9; color: #1e293b; }
    h1, h2, h3 { color: #0f172a !important; font-weight: 700 !important; }
    
    /* Floating Button */
    button[title="Toggle Theme"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important;
        z-index: 9999999 !important; width: 60px !important; height: 60px !important;
        border-radius: 50% !important; background: rgba(255, 255, 255, 0.95) !important;
        backdrop-filter: blur(15px) !important; border: 1px solid rgba(255, 255, 255, 1) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
    }
</style>
"""

# Render Tema
if st.session_state.theme_mode == "dark":
    st.markdown(CSS_DARK_MODE, unsafe_allow_html=True)
    ikon_tema = "☀️"
else:
    st.markdown(CSS_LIGHT_MODE, unsafe_allow_html=True)
    ikon_tema = "🌙"

st.button(ikon_tema, on_click=toggle_theme, help="Toggle Theme")

# [.... Kode logika perhitungan tetap sama seperti sebelumnya ....]
# (Bagian logika variabel: count_warna, count_bw, grand_total, dll. tetap sama)

# --- BLOK RENDER TABEL (BAGIAN YANG DIUBAH) ---
    st.markdown("### 💰 Ringkasan Biaya Produksi")
    
    # Membuat tabel kustom dengan HTML
    table_html = f"""
    <table style="width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 15px; overflow: hidden; border: 1px solid rgba(128,128,128,0.2);">
        <thead>
            <tr style="background: linear-gradient(135deg, #f09433 0%, #e6683c 30%, #dc2743 60%, #bc1888 100%); color: white;">
                <th style="padding: 15px; text-align: left; font-weight: 700; font-size: 16px;">Spesifikasi Buku & Komponen</th>
                <th style="padding: 15px; text-align: left; font-weight: 700; font-size: 16px;">Detail Perhitungan</th>
            </tr>
        </thead>
        <tbody style="background: {'rgba(30, 41, 59, 0.5)' if st.session_state.theme_mode == 'dark' else 'rgba(255, 255, 255, 0.8)'};">
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1);">Ukuran & Bahan Kertas Isi</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1); font-weight: 500;">{ukuran_buku} | Kertas {jenis_kertas} ({mode_cetak})</td>
            </tr>
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1);">Jilid Cover Buku</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1); font-weight: 500;">{jenis_jilid}</td>
            </tr>
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1);">Cetak Isi (Warna & BW) x {jumlah_cetak} Eks</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1); font-weight: 500;">Rp {total_isi_all:,} (Diskon Isi {diskon_isi_persen}%)</td>
            </tr>
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1);">Finishing Jilid x {jumlah_cetak} Eks</td>
                <td style="padding: 12px; border-bottom: 1px solid rgba(128,128,128,0.1); font-weight: 500;">Rp {total_finishing_all:,} (Diskon Finishing {persen_diskon_finishing}%)</td>
            </tr>
            <tr style="background: {'rgba(16, 185, 129, 0.1)' if st.session_state.theme_mode == 'dark' else 'rgba(16, 185, 129, 0.1)'};">
                <td style="padding: 12px; font-weight: 700;">PILIHAN 1: GRAND TOTAL (Lunas)</td>
                <td style="padding: 12px; font-weight: 700; color: #10b981;">Rp {grand_total:,}</td>
            </tr>
            <tr>
                <td style="padding: 12px;">PILIHAN 2: NOMINAL UANG MUKA (DP 50%)</td>
                <td style="padding: 12px; font-weight: 700;">Rp {nominal_dp:,}</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
