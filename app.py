import copy
import json
import hashlib
from urllib.parse import quote
import fitz
import streamlit as st
from engine import parse_page_input, add_duplex_pairs, split_pdf_by_pages, process_and_split_pdf, format_rupiah as rp
from settings import DEFAULT, setup, read, save, calculate, validate

st.set_page_config(page_title='Litnus • Studio Cetak', page_icon='📚', layout='wide')

# Custom UI/UX Styling mengadaptasi tema Dashboard Referensi
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    color: #1a3c39;
}

/* Background canvas gradien sage pastel */
.stApp {
    background: radial-gradient(circle at 10% 10%, #edf7f5 0%, #d8eae6 50%, #cde4df 100%);
    background-attachment: fixed;
}

.block-container {
    max-width: 1280px;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background-color: rgba(235, 246, 243, 0.75) !important;
    backdrop-filter: blur(16px);
    border-right: 1px solid rgba(255, 255, 255, 0.7);
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] h1 {
    font-size: 1.45rem;
    font-weight: 800;
    color: #07433f;
    letter-spacing: -0.03em;
    margin-bottom: 1.5rem;
}

/* Navigation button: Pill shape sesuai referensi */
.st-key-workspace_nav button, .st-key-admin_nav button {
    min-height: 46px;
    justify-content: flex-start;
    text-align: left;
    border-radius: 14px !important;
    border: none !important;
    background: transparent !important;
    color: #386460 !important;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: none !important;
    margin-bottom: 0.35rem;
}

.st-key-workspace_nav button:hover, .st-key-admin_nav button:hover {
    background: rgba(255, 255, 255, 0.6) !important;
    color: #054440 !important;
    transform: translateX(3px);
}

.st-key-workspace_nav button[kind="primary"], .st-key-admin_nav button[kind="primary"] {
    background: linear-gradient(135deg, #0d7370 0%, #054643 100%) !important;
    color: #ffffff !important;
    font-weight: 700;
    box-shadow: 0 8px 20px rgba(5, 70, 67, 0.22) !important;
}

.st-key-workspace_nav button img, .st-key-admin_nav button img {
    width: 20px;
    height: 20px;
    margin-right: 0.65rem;
    vertical-align: middle;
}

.st-key-admin_nav {
    border-top: 1px solid rgba(7, 75, 70, 0.12);
    padding-top: 1rem;
    margin-top: 1rem;
}

/* Header greeting ala CoachPro */
.dashboard-topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.4rem;
}
.welcome-badge {
    font-size: 0.92rem;
    font-weight: 600;
    color: #0c7370;
    letter-spacing: -0.01em;
}
.dashboard-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #063936;
    letter-spacing: -0.035em;
    margin: 0.15rem 0 0.5rem 0;
}

/* Card container glassmorphic */
.glass-card {
    background: rgba(255, 255, 255, 0.88);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.9);
    border-radius: 22px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 12px 32px rgba(9, 64, 60, 0.05);
}

.glass-card-header {
    font-size: 1.15rem;
    font-weight: 700;
    color: #063936;
    margin-bottom: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Custom mini stat-cards */
.stat-pill-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 1rem;
}

.stat-pill {
    background: #ffffff;
    border-radius: 18px;
    padding: 1rem;
    display: flex;
    align-items: center;
    gap: 12px;
    box-shadow: 0 4px 18px rgba(10, 50, 48, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.8);
}

.stat-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
}

.stat-content {
    display: flex;
    flex-direction: column;
}

.stat-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #648683;
}

.stat-value {
    font-size: 1.35rem;
    font-weight: 800;
    color: #083c39;
    line-height: 1.2;
}

/* Form input adjustments */
div[data-baseweb="input"], div[data-baseweb="select"] > div {
    background-color: #ffffff !important;
    border-radius: 12px !important;
    border-color: #c9dedb !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #0b6b69 !important;
    box-shadow: 0 0 0 2px rgba(11, 107, 105, 0.2) !important;
}

/* Action Banner ala "Setup training for next week" */
.promo-banner {
    background: linear-gradient(135deg, #096a66 0%, #034845 100%);
    border-radius: 20px;
    padding: 1.5rem 1.6rem;
    color: #ffffff;
    position: relative;
    overflow: hidden;
    margin-top: 1rem;
    box-shadow: 0 14px 28px rgba(6, 60, 56, 0.25);
}
.promo-banner h3 {
    color: #ffffff;
    font-size: 1.25rem;
    font-weight: 700;
    margin: 0.3rem 0 1rem 0;
    max-width: 75%;
}
.promo-banner .tagline {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #79dbd6;
}

/* Download buttons */
.stDownloadButton button {
    border-radius: 12px !important;
    min-height: 44px;
    font-weight: 600;
    border: 1px solid #c9dfdb !important;
}

.stButton button[kind="primary"] {
    background: linear-gradient(135deg, #0d7370 0%, #064b48 100%) !important;
    border-radius: 12px !important;
    border: none;
    font-weight: 600;
}
</style>''', unsafe_allow_html=True)

MENU = {
    'Kalkulator Cepat': ('Jumlah halaman saja', '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h2m4 0h2m-8 4h2m4 0h2"/>'),
    'Deteksi Warna PDF': ('Analisis warna otomatis', '<path d="M12 3s-6 7-6 12a6 6 0 0 0 12 0c0-5-6-12-6-12Z"/><path d="M9 15a3 3 0 0 0 3 3"/>'),
    'Pilah Halaman PDF': ('Pilih halaman manual', '<path d="M7 3h8l4 4v14H7zM15 3v5h4M10 12h6m-6 4h6"/>'),
    'Admin Tarif': (None, '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>'),
}


def icon_svg(path, color='#087580'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'


def go_to(page):
    st.session_state['workspace'] = page


def draft_widget(widget, field, label, **kwargs):
    stored = f'draft:{method}:{field}'
    key = f'widget:{stored}'
    if key not in st.session_state and stored in st.session_state:
        st.session_state[key] = st.session_state[stored]
        kwargs.pop('value', None)
        kwargs.pop('index', None)
    value = widget(label, key=key, **kwargs)
    st.session_state[stored] = value
    return value


def remember_pdf(upload_key, pdf_key):
    upload = st.session_state[upload_key]
    if upload is not None:
        st.session_state[pdf_key] = (upload.name, upload.getvalue())
    else:
        st.session_state.pop(pdf_key, None)


def remove_pdf(upload_key, pdf_key):
    st.session_state.pop(pdf_key, None)
    st.session_state.pop(upload_key, None)


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
else:
    st.caption('Mode pratinjau: memakai tarif bawaan.')

logged_in = st.user.get('is_logged_in', False)
admin = logged_in and st.user.get('email') in secrets.get('admin_emails', [])
screen = st.session_state.setdefault('workspace', 'Admin Tarif' if logged_in else 'Kalkulator Cepat')
theme = getattr(getattr(st.context, 'theme', None), 'type', None)

# --- SIDEBAR (Mirip CoachPro left menu) ---
with st.sidebar:
    st.markdown('''
        <div style="padding: 0.5rem 0.2rem 1.2rem 0.2rem;">
            <div style="font-size: 1.5rem; font-weight: 800; color: #06403d; letter-spacing: -0.04em;">
                Litnus<span style="color: #10a299;">Pro</span>
            </div>
            <div style="font-size: 0.78rem; font-weight: 600; color: #558581;">STUDIO CETAK & ANALISIS</div>
        </div>
    ''', unsafe_allow_html=True)
    
    tools_nav = st.container(key='workspace_nav')
    admin_nav = st.container(key='admin_nav')
    for page, (method_name, path) in MENU.items():
        active = screen == page
        icon_color = '#ffffff' if active else '#0b6b69'
        icon = quote(icon_svg(path, icon_color), safe='')
        with tools_nav if method_name else admin_nav:
            st.button(
                f'![](data:image/svg+xml,{icon}) {page}',
                key=f'nav_{page}', type='primary' if active else 'secondary',
                on_click=go_to, args=(page,), use_container_width=True,
            )
    st.markdown('<div style="height: 40px;"></div>', unsafe_allow_html=True)
    st.caption(f'Versi tarif aktif: **{version or "bawaan"}**')
    if logged_in:
        st.button('Keluar', on_click=st.logout, use_container_width=True)

# --- HALAMAN ADMIN TARIF ---
if screen == 'Admin Tarif':
    if not admin:
        badge = icon_svg(MENU['Admin Tarif'][1], '#0b6b69')
        with st.container(key='login_panel'):
            st.markdown(f'''
                <div class="glass-card" style="text-align: center; max-width: 480px; margin: 3rem auto;">
                    <div style="margin-bottom: 1rem;">{badge}</div>
                    <h2 style="font-size: 1.6rem; font-weight: 800; color: #063936;">Ruang Admin</h2>
                    <p style="color: #55807c; font-size: 0.95rem;">Masuk dengan akun terdaftar untuk mengelola tarif dan diskon cetak.</p>
                </div>
            ''', unsafe_allow_html=True)
            if logged_in:
                st.warning('Akun ini belum terdaftar sebagai admin. Keluar untuk memakai akun lain.')
            elif 'auth' in secrets:
                if st.button('Masuk dengan Google', key='google_login', type='primary', use_container_width=True):
                    st.login()
            else:
                st.info('Login belum dikonfigurasi. Ikuti panduan secrets.toml untuk mengaktifkannya.')
            st.button('Kembali ke Kalkulator', key='guest_login', on_click=go_to, args=('Kalkulator Cepat',), use_container_width=True)
        st.stop()

    st.markdown('<div class="welcome-badge">Admin Workspace</div><h1 class="dashboard-title">Tarif & Konfigurasi Biaya</h1>', unsafe_allow_html=True)
    if not configured:
        st.info('Hubungkan database terlebih dahulu.')
        st.stop()
    draft = copy.deepcopy(config)
    rows = []
    for size, p in config['prices'].items():
        for paper in ['HVS 70', 'BP 57']:
            rows.append(dict(Ukuran=size, Kertas=paper, Warna=p[paper]['warna'], BW=p[paper]['bw'], Finishing=p['base_finishing_soft']))
    
    st.caption('Tarif per halaman dan finishing per eksemplar. Finishing pada kedua baris kertas untuk ukuran yang sama harus sama.')
    edited = st.data_editor(rows, disabled=['Ukuran', 'Kertas'], hide_index=True, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    draft['simplex'] = c1.number_input('Pengali simplex', min_value=0.1, value=float(config['simplex']))
    draft['hardcover'] = c2.number_input('Pengali hardcover', min_value=0.1, value=float(config['hardcover']))
    draft['dp'] = c3.number_input('DP (%)', 0, 100, int(config['dp']))
    
    st.write('**Diskon isi berdasarkan jumlah eksemplar**')
    draft['tiers'] = st.data_editor(config['tiers'], num_rows='dynamic', key='tiers', hide_index=True)
    c1, c2, c3 = st.columns(3)
    draft['finishing_step'] = c1.number_input('Interval jumlah finishing', 1, value=int(config['finishing_step']))
    draft['finishing_discount'] = c2.number_input('Tambahan diskon (%)', 0, 100, int(config['finishing_discount']))
    draft['finishing_cap'] = c3.number_input('Batas diskon finishing (%)', 0, 100, int(config['finishing_cap']))
    try:
        finishing = {}
        for row in edited:
            size = row['Ukuran']
            val = row['Finishing']
            if size in finishing and finishing[size] != val:
                raise ValueError('Finishing untuk ukuran yang sama harus konsisten.')
            finishing[size] = val
            draft['prices'][size]['base_finishing_soft'] = val
            draft['prices'][size][row['Kertas']] = {'warna': row['Warna'], 'bw': row['BW']}
        validate(draft)
        size = list(config['prices'])[0]
        old = calculate(config, size, 'HVS 70', 'Duplex (Bolak-balik)', 'Soft Cover', 10, 0, 100)
        new = calculate(draft, size, 'HVS 70', 'Duplex (Bolak-balik)', 'Soft Cover', 10, 0, 100)
        st.metric('Simulasi: A5 HVS 70 100 hal BW 10 eks', rp(new['total']), rp(new['total'] - old['total']))
        reason = st.text_input('Alasan perubahan')
        if st.button('Simpan dan terapkan harga', type='primary', disabled=not reason.strip()):
            save(draft, version, reason.strip())
            st.success('Harga tersimpan.')
            st.rerun()
    except (ValueError, TypeError, KeyError):
        st.error('Periksa tarif, jenjang diskon, dan kesamaan finishing sebelum menyimpan.')
    
    from settings import connect
    with st.expander('Riwayat perubahan'):
        with connect() as c:
            records = c.execute('SELECT created_at,actor,reason,old_data,new_data FROM litnus_history ORDER BY id DESC LIMIT 100').fetchall()
        for date, actor, reason, old, new in records:
            with st.expander(f'{date} • {actor} • {reason}'):
                st.json({'sebelum': old, 'sesudah': new})
    st.stop()

# --- WORKSPACE DASHBOARD (Main App) ---
method = MENU[screen][0]
user_display = (st.user.get('name') or st.user.get('email', 'Tamu')).split('@')[0].capitalize() if logged_in else 'Editor'

# Top Bar ala CoachPro (Welcome back & Title)
st.markdown(f'''
    <div class="dashboard-topbar">
        <div>
            <div class="welcome-badge">Welcome back, {user_display} 👋</div>
            <div class="dashboard-title">Dashboard Produksi</div>
        </div>
    </div>
''', unsafe_allow_html=True)

# Layout 2 Kolom (Kiri: Naskah & Spek, Kanan: Metrik, Biaya & Aksi)
col_left, col_right = st.columns([1.65, 1], gap='large')

with col_left:
    st.markdown('<div class="glass-card"><div class="glass-card-header">1. Naskah Buku</div>', unsafe_allow_html=True)
    title = draft_widget(st.text_input, 'title', 'Judul buku', value='Pesanan Litnus')
    uploaded = None
    color = bw = 0
    cb = bb = None
    colors = []
    blacks = []

    if method != 'Jumlah halaman saja':
        upload_key, pdf_key = f'upload:{method}', f'pdf:{method}'
        st.file_uploader(
            'Unggah file PDF isi buku', type='pdf', key=upload_key,
            on_change=remember_pdf, args=(upload_key, pdf_key),
        )
        uploaded = st.session_state.get(pdf_key)
        if uploaded:
            st.caption(f'PDF aktif · **{uploaded[0]}**')
            st.button('Lepas PDF', key=f'remove:{method}', on_click=remove_pdf, args=(upload_key, pdf_key))
        if method == 'Pilih halaman manual':
            roman = draft_widget(
                st.number_input, 'roman', 'Jumlah halaman preliminaries',
                min_value=0, value=12, step=1,
                help='Halaman awal sebelum halaman 1 utama (kata pengantar, daftar isi, dll).'
            )
            selection = draft_widget(st.text_area, 'selection', 'Halaman cetak warna', placeholder='iii-v, 1, 5-9')
    else:
        c_a, c_b = st.columns(2)
        color = draft_widget(c_a.number_input, 'color', 'Jumlah halaman warna', min_value=0, value=0)
        bw = draft_widget(c_b.number_input, 'bw', 'Jumlah halaman BW', min_value=0, value=0)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass-card"><div class="glass-card-header">2. Spesifikasi Cetak & Jilid</div>', unsafe_allow_html=True)
    sa, sb = st.columns(2)
    size = draft_widget(sa.selectbox, 'size', 'Ukuran buku', options=list(config['prices']))
    paper = draft_widget(sb.selectbox, 'paper', 'Jenis kertas', options=['HVS 70', 'BP 57'])
    mode = draft_widget(sa.selectbox, 'mode', 'Mode cetak', options=['Duplex (Bolak-balik)', 'Simplex (Satu Sisi)'])
    binding = draft_widget(sb.selectbox, 'binding', 'Tipe jilid', options=['Soft Cover', 'Hard Cover'])
    qty = draft_widget(st.number_input, 'qty', 'Jumlah eksemplar', min_value=1, value=1)
    
    override = None
    if admin:
        with st.expander('Diskon khusus pesanan'):
            if draft_widget(st.checkbox, 'override_enabled', 'Ganti diskon isi otomatis'):
                override = draft_widget(st.number_input, 'override', 'Diskon isi (%)', min_value=0, max_value=100, value=0)

    if uploaded:
        data = uploaded[1]
        try:
            with fitz.open(stream=data, filetype='pdf') as doc:
                if doc.needs_pass:
                    raise ValueError('PDF terkunci kata sandi.')
                total = len(doc)
            if total < 1:
                raise ValueError('PDF tidak memiliki halaman.')
            st.caption(f'Total halaman terdeteksi: {total}')
            if method == 'Analisis warna otomatis':
                with st.expander('Opsi analisis'):
                    force = draft_widget(st.checkbox, 'force_bw', 'Konversi semua ke BW')
                    sensitivity = draft_widget(st.slider, 'sensitivity', 'Sensitivitas kontras', 5, 50, 25)
                    pct = draft_widget(st.slider, 'pct', 'Minimal area warna (%)', 0.01, 5.0, 0.1)
                if st.button('Mulai Analisis PDF', type='primary'):
                    with st.spinner('Menganalisis halaman...'):
                        st.session_state['analysis'] = (hashlib.sha256(data).hexdigest(), mode, force, sensitivity, pct, process_and_split_pdf(data, force, sensitivity, pct, mode, total))
                saved = st.session_state.get('analysis')
                if saved and saved[:5] == (hashlib.sha256(data).hexdigest(), mode, force, sensitivity, pct):
                    colors, blacks, cb, bb, _ = saved[5]
                else:
                    st.info('Klik tombol di atas untuk menjalankan analisis warna.')
                    colors = []
                    blacks = []
            else:
                if roman > total:
                    raise ValueError(f'Preliminaries melebihi total {total} halaman.')
                pair = draft_widget(st.checkbox, 'pair', 'Sertakan pasangan duplex', value=True, disabled=mode.startswith('Simplex'))
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
    st.markdown('</div>', unsafe_allow_html=True)

    # Rincian Halaman
    if colors or blacks:
        with st.expander('Rincian nomor halaman PDF terurai'):
            st.write('Warna:', ', '.join(map(str, colors)) or 'Tidak ada')
            st.write('BW:', ', '.join(map(str, blacks)) or 'Tidak ada')

with col_right:
    # Card Rangkuman Statistik Ala Referensi (Possession, Price, Budget)
    if color + bw == 0:
        st.markdown('''
            <div class="glass-card" style="text-align: center; padding: 2.5rem 1.5rem;">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📊</div>
                <div style="font-weight: 700; color: #06403d; font-size: 1.1rem;">Estimasi Belum Tersedia</div>
                <div style="color: #648683; font-size: 0.88rem; margin-top: 0.35rem;">Lengkapi data naskah & halaman di sebelah kiri untuk menghitung biaya cetak.</div>
            </div>
        ''', unsafe_allow_html=True)
    else:
        r = calculate(config, size, paper, mode, binding, qty, color, bw, override)
        
        # Pill Metrik Grid (Mengadopsi 4 Kartu UI Referensi: Ungu, Merah Muda, Oranye, Teal)
        st.markdown(f'''
            <div class="stat-pill-grid">
                <div class="stat-pill">
                    <div class="stat-icon" style="background: #e9e5ff; color: #7257ff;">🎨</div>
                    <div class="stat-content">
                        <span class="stat-label">HAL. WARNA</span>
                        <span class="stat-value">{color}</span>
                    </div>
                </div>
                <div class="stat-pill">
                    <div class="stat-icon" style="background: #ffe3f0; color: #e83e8c;">📄</div>
                    <div class="stat-content">
                        <span class="stat-label">HAL. HITAM PUTIH</span>
                        <span class="stat-value">{bw}</span>
                    </div>
                </div>
                <div class="stat-pill">
                    <div class="stat-icon" style="background: #fff0d8; color: #e67e22;">🏷️</div>
                    <div class="stat-content">
                        <span class="stat-label">HARGA / EKS</span>
                        <span class="stat-value" style="font-size: 1.05rem;">{rp(r['unit'])}</span>
                    </div>
                </div>
                <div class="stat-pill">
                    <div class="stat-icon" style="background: #d4f4f0; color: #0b8a82;">📦</div>
                    <div class="stat-content">
                        <span class="stat-label">EKSEMPLAR</span>
                        <span class="stat-value">{qty}</span>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        # Kartu Ringkasan Pembayaran Utama
        st.markdown(f'''
            <div class="glass-card" style="padding: 1.5rem;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #58807c; letter-spacing: 0.05em; text-transform: uppercase;">TOTAL TAGIHAN</div>
                <div style="font-size: 2.2rem; font-weight: 800; color: #06403d; margin: 0.2rem 0 1rem 0;">{rp(r['total'])}</div>
                <div style="display: flex; justify-content: space-between; border-top: 1px solid #e1eee9; padding-top: 0.8rem; font-size: 0.9rem;">
                    <span style="color: #55807c;">DP Wajib ({config['dp']}%)</span>
                    <strong style="color: #06403d;">{rp(r['dp'])}</strong>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 0.4rem; font-size: 0.9rem;">
                    <span style="color: #55807c;">Diskon Cetak Isi</span>
                    <strong style="color: #0d7370;">{r['discount']}%</strong>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 0.4rem; font-size: 0.9rem;">
                    <span style="color: #55807c;">Diskon Finishing</span>
                    <strong style="color: #0d7370;">{r['finishing_discount']}%</strong>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        receipt = f"LITNUS PRINTING\nESTIMASI BIAYA\n{title}\nTarif versi {version}\n{size} | {paper} | {mode} | {binding}\n{color} halaman warna + {bw} BW\n{qty} eksemplar\nHarga/eks: {rp(r['unit'])}\nTotal: {rp(r['total'])}\nDP {config['dp']}%: {rp(r['dp'])}\nDiskon isi {r['discount']}% | finishing {r['finishing_discount']}%\nHalaman PDF warna: {colors}\nHalaman PDF BW: {blacks}\nDokumen estimasi, bukan bukti pembayaran."
        st.download_button('Unduh Estimasi Biaya (TXT)', receipt, 'Estimasi_Litnus.txt', 'text/plain', use_container_width=True)

        invoice = f"""LITNUS PRINTING
NOTA TAGIHAN CETAK

Judul buku: {title}
Ukuran dan kertas: {size} | {paper}
Mode cetak dan jilid: {mode} | {binding}
Isi buku: {color} halaman warna + {bw} halaman hitam putih
Jumlah cetak: {qty} eksemplar
Harga per eksemplar: {rp(r['unit'])}
Diskon isi: {r['discount']}% | Diskon finishing: {r['finishing_discount']}%

TOTAL TAGIHAN: {rp(r['total'])}
Pilihan pembayaran lunas: {rp(r['total'])}
Pilihan DP {config['dp']}%: {rp(r['dp'])}
Sisa setelah DP: {rp(r['total'] - r['dp'])}

Silakan transfer sesuai pilihan pembayaran:
Mandiri: 144-00-2306065-7 (a/n PT Literasi Nusantara Abadi Grup)
BCA: 117-737-3737 (a/n PT Literasi Nusantara Abadi Grup)

Mohon kirim bukti transfer setelah pembayaran. Terima kasih."""

        st.download_button(
            'Unduh Nota Tagihan Resmi (TXT)',
            invoice,
            'Nota_Tagihan_Litnus.txt',
            'text/plain; charset=utf-8',
            use_container_width=True,
        )

        if cb:
            st.download_button('Unduh File Pisah: PDF Warna', cb, 'Litnus_Warna.pdf', 'application/pdf', use_container_width=True)
        if bb:
            st.download_button('Unduh File Pisah: PDF Hitam Putih', bb, 'Litnus_BW.pdf', 'application/pdf', use_container_width=True)

        with st.expander('Rincian Tarif Dasar'):
            st.write({'Warna/hlm': rp(r['color_rate']), 'BW/hlm': rp(r['bw_rate']), 'Finishing/eks': rp(r['finishing'])})

    # Banner Ajakan Aksi (Mengadopsi kartu promo hijau "Setup training for next week")
    st.markdown('''
        <div class="promo-banner">
            <span class="tagline">PANDUAN CETAK</span>
            <h3>Cek dummy naskah sebelum cetak massal</h3>
            <p style="font-size: 0.85rem; color: #b7e3e0; margin: 0;">Pastikan format margin, resolusi gambar (300 DPI), serta bleed 3mm sudah terpenuhi.</p>
        </div>
    ''', unsafe_allow_html=True)
