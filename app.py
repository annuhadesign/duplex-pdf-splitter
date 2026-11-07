import copy
import json
import hashlib
from urllib.parse import quote
import fitz
import streamlit as st
from engine import parse_page_input, add_duplex_pairs, split_pdf_by_pages, process_and_split_pdf, format_rupiah as rp
from settings import DEFAULT, setup, read, save, calculate, validate

st.set_page_config(page_title='Litnus • Studio Cetak',page_icon='📚',layout='wide')
st.markdown('''<style>
.block-container { max-width: 1200px; padding-top: 5rem; }
.stApp { background-image: radial-gradient(ellipse at 0% 0%, #46b3a91e, transparent 65%); }
[data-testid="stSidebar"] { border-right: 1px solid #75a9a64d; }
.st-key-workspace_nav button, .st-key-admin_nav button {
    min-height: 44px; justify-content: flex-start; text-align: left;
    border-color: transparent; background: transparent;
}
.st-key-workspace_nav button:hover, .st-key-admin_nav button:hover { border-color: currentColor; }
.st-key-workspace_nav button[kind="primary"], .st-key-admin_nav button[kind="primary"] {
    background: #086570; color: #fff;
}
.st-key-workspace_nav button img, .st-key-admin_nav button img {
    width: 18px; height: 18px; vertical-align: middle; margin-right: .45rem;
}
.st-key-admin_nav { border-top: 1px solid #79a9a766; padding-top: .75rem; }
.intro {
    padding: 26px 30px;
    background: #46b3a912;
    border: 1px solid #46b3a94d;
    border-radius: 20px;
    margin-bottom: 18px;
}
.intro h1 { letter-spacing: -.04em; margin: 0 0 8px; }
.intro p { margin: 0; }
.st-key-login_panel {
    max-width: 460px; margin: 1rem auto; padding: clamp(1rem, 4vw, 2.25rem);
    background: linear-gradient(145deg, #f3f7ff, #d7e5ff);
    border: 1px solid white; border-radius: 30px;
    box-shadow: 12px 16px 38px #28478630, inset 2px 2px 8px white;
}
.login-card { text-align: center; color: #182c58; }
.login-card h1 { color: #182c58; font-size: 2rem; margin: .5rem 0; }
.st-key-google_login button { background: #2355cb; color: white; min-height: 46px; }
.st-key-guest_login button { background: #f3f7ff; color: #182c58; border-color: #7892c7; min-height: 44px; }
.st-key-google_login button:focus-visible, .st-key-guest_login button:focus-visible { outline: 3px solid #345bb0; outline-offset: 2px; }
div[data-testid="stMetric"] {
    background: #eaf8f650;
    border: 1px solid #ffffff75;
    padding: 18px;
    border-radius: 16px;
}
@media (max-width: 600px) {
    .block-container { padding-inline: 1rem; padding-top: 4.5rem; }
    .intro { padding: 18px; }
    .intro h1 { font-size: 30px; }
}
</style>''',unsafe_allow_html=True)

MENU = {
    'Kalkulator Cepat': ('Jumlah halaman saja', '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 8h8M8 12h2m4 0h2m-8 4h2m4 0h2"/>'),
    'Deteksi Warna PDF': ('Analisis warna otomatis', '<path d="M12 3s-6 7-6 12a6 6 0 0 0 12 0c0-5-6-12-6-12Z"/><path d="M9 15a3 3 0 0 0 3 3"/>'),
    'Pilah Halaman PDF': ('Pilih halaman manual', '<path d="M7 3h8l4 4v14H7zM15 3v5h4M10 12h6m-6 4h6"/>'),
    'Admin Tarif': (None, '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>'),
}


def icon_svg(path, color='#087580'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{path}</svg>'


def go_to(page):
    st.session_state['workspace'] = page


def draft_widget(widget, field, label, **kwargs):
    """Restore widget values after Streamlit removes widgets from another menu."""
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
configured='database' in secrets
version=0; config=copy.deepcopy(DEFAULT)
if configured:
    try: setup(); version,config=read()
    except Exception:
        st.error('Penyimpanan harga belum dapat diakses. Periksa koneksi database sebelum melanjutkan.'); st.stop()
else: st.warning('Mode pratinjau: memakai tarif bawaan. Hubungkan database untuk menyimpan harga admin.')
logged_in=st.user.get('is_logged_in',False)
admin=logged_in and st.user.get('email') in secrets.get('admin_emails',[])
screen = st.session_state.setdefault('workspace', 'Admin Tarif' if logged_in else 'Kalkulator Cepat')
theme = getattr(getattr(st.context, 'theme', None), 'type', None)
with st.sidebar:
    st.title('Litnus Printing')
    tools_nav = st.container(key='workspace_nav')
    admin_nav = st.container(key='admin_nav')
    for page, (method_name, path) in MENU.items():
        active = screen == page
        icon_color = '#ffffff' if active else ('#7edce0' if theme == 'dark' else '#086570')
        icon = quote(icon_svg(path, icon_color), safe='')
        with tools_nav if method_name else admin_nav:
            st.button(
                f'![](data:image/svg+xml,{icon}) {page}',
                key=f'nav_{page}', type='primary' if active else 'secondary',
                on_click=go_to, args=(page,), use_container_width=True,
            )
    st.caption(f'Versi tarif: {version or "bawaan"}')
    if logged_in: st.button('Keluar',on_click=st.logout)
if screen=='Admin Tarif':
    if not admin:
        badge = icon_svg(MENU['Admin Tarif'][1])
        with st.container(key='login_panel'):
            st.markdown(f'<div class="login-card">{badge}<h1>Ruang Admin</h1><p>Masuk untuk mengelola tarif dan diskon cetak.</p></div>', unsafe_allow_html=True)
            if logged_in:
                st.warning('Akun ini belum terdaftar sebagai admin. Keluar untuk memakai akun lain.')
            elif 'auth' in secrets:
                if st.button('Masuk dengan Google', key='google_login', type='primary', use_container_width=True):
                    st.login()
            else:
                st.info('Login belum dikonfigurasi. Ikuti README untuk mengaktifkannya.')
            st.button('Lanjut tanpa login', key='guest_login', on_click=go_to, args=('Kalkulator Cepat',), use_container_width=True)
        st.stop()
    st.subheader('Harga dan diskon')
    if not configured: st.info('Hubungkan database terlebih dahulu.'); st.stop()
    draft=copy.deepcopy(config)
    rows=[]
    for size,p in config['prices'].items():
        for paper in ['HVS 70','BP 57']: rows.append(dict(Ukuran=size,Kertas=paper,Warna=p[paper]['warna'],BW=p[paper]['bw'],Finishing=p['base_finishing_soft']))
    st.caption('Tarif per halaman dan finishing per eksemplar. Finishing pada kedua baris kertas untuk ukuran yang sama harus sama.')
    edited=st.data_editor(rows,disabled=['Ukuran','Kertas'],hide_index=True,use_container_width=True)
    c1,c2,c3=st.columns(3)
    draft['simplex']=c1.number_input('Pengali simplex',min_value=0.1,value=float(config['simplex']))
    draft['hardcover']=c2.number_input('Pengali hardcover',min_value=0.1,value=float(config['hardcover']))
    draft['dp']=c3.number_input('DP (%)',0,100,int(config['dp']))
    st.write('Diskon isi berdasarkan jumlah eksemplar')
    draft['tiers']=st.data_editor(config['tiers'],num_rows='dynamic',key='tiers',hide_index=True)
    c1,c2,c3=st.columns(3)
    draft['finishing_step']=c1.number_input('Interval jumlah finishing',1,value=int(config['finishing_step']))
    draft['finishing_discount']=c2.number_input('Tambahan diskon (%)',0,100,int(config['finishing_discount']))
    draft['finishing_cap']=c3.number_input('Batas diskon finishing (%)',0,100,int(config['finishing_cap']))
    try:
        finishing={}
        for row in edited:
            size=row['Ukuran']; val=row['Finishing']
            if size in finishing and finishing[size]!=val: raise ValueError('Finishing untuk ukuran yang sama harus konsisten.')
            finishing[size]=val
            draft['prices'][size]['base_finishing_soft']=val
            draft['prices'][size][row['Kertas']]={'warna':row['Warna'],'bw':row['BW']}
        validate(draft)
        st.caption('Simulasi: A5 HVS 70, duplex, soft cover, 100 halaman BW, 10 eksemplar.')
        size=list(config['prices'])[0]
        old=calculate(config,size,'HVS 70','Duplex (Bolak-balik)','Soft Cover',10,0,100)
        new=calculate(draft,size,'HVS 70','Duplex (Bolak-balik)','Soft Cover',10,0,100)
        st.metric('Total setelah perubahan',rp(new['total']),rp(new['total']-old['total']))
        reason=st.text_input('Alasan perubahan')
        if st.button('Simpan dan terapkan harga',type='primary',disabled=not reason.strip()):
            save(draft,version,reason.strip()); st.success('Harga tersimpan.'); st.rerun()
    except (ValueError,TypeError,KeyError): st.error('Periksa tarif, jenjang diskon, dan kesamaan finishing sebelum menyimpan.')
    from settings import connect
    with st.expander('Riwayat perubahan'):
        with connect() as c:
            records=c.execute('SELECT created_at,actor,reason,old_data,new_data FROM litnus_history ORDER BY id DESC LIMIT 100').fetchall()
        for date,actor,reason,old,new in records:
            with st.expander(f'{date} • {actor} • {reason}'):
                st.json({'sebelum':old,'sesudah':new})
    st.stop()

method = MENU[screen][0]
st.markdown('<div class="intro"><h1>Studio Cetak Litnus</h1><p>Dari naskah hingga siap produksi.</p></div>', unsafe_allow_html=True)
heading, information = st.columns([8, 1])
heading.header(screen)
with information.popover('ⓘ', help='Petunjuk menu'):
    st.write({
        'Kalkulator Cepat': 'Masukkan jumlah halaman warna dan hitam putih untuk menghitung biaya tanpa PDF.',
        'Deteksi Warna PDF': 'Unggah PDF dan tekan Analisis PDF. Hasilnya mengikuti pengaturan deteksi dan mode cetak.',
        'Pilah Halaman PDF': 'Unggah PDF, isi jumlah preliminaries, lalu tulis halaman warna. Nomor isi 1 dihitung setelah preliminaries.',
    }[screen])
    st.caption('Draf tiap menu tersimpan selama sesi ini.')
left,right=st.columns([1.7,1],gap='large')
with left:
    st.subheader('Naskah')
    title = draft_widget(st.text_input, 'title', 'Judul buku', value='Pesanan Litnus')
    uploaded=None; color=bw=0; cb=bb=None; colors=[]; blacks=[]
    if method!='Jumlah halaman saja':
        upload_key, pdf_key = f'upload:{method}', f'pdf:{method}'
        st.file_uploader(
            'Unggah PDF isi buku', type='pdf', key=upload_key,
            on_change=remember_pdf, args=(upload_key, pdf_key),
        )
        uploaded = st.session_state.get(pdf_key)
        if uploaded:
            st.caption(f'PDF aktif · {uploaded[0]}')
            st.button('Lepas PDF', key=f'remove:{method}', on_click=remove_pdf, args=(upload_key, pdf_key))
        if method == 'Pilih halaman manual':
            roman = draft_widget(
                st.number_input, 'roman', 'Jumlah halaman preliminaries',
                min_value=0, value=12, step=1,
                help='Hitung halaman PDF sebelum halaman isi bernomor 1. Isi 0 jika tidak ada.',
            )
            st.caption(f'Halaman isi 1 berada pada halaman PDF {roman + 1}.')
            selection = draft_widget(st.text_area, 'selection', 'Halaman warna', placeholder='iii-v, 1, 5-9', help='Gunakan nomor Romawi untuk halaman awal dan nomor angka untuk isi buku. Pisahkan dengan koma.')
    else:
        a, b = st.columns(2)
        color = draft_widget(a.number_input, 'color', 'Halaman warna', min_value=0, value=0)
        bw = draft_widget(b.number_input, 'bw', 'Halaman BW', min_value=0, value=0)
    st.subheader('2. Spesifikasi')
    a,b=st.columns(2)
    size = draft_widget(a.selectbox, 'size', 'Ukuran', options=list(config['prices']))
    paper = draft_widget(b.selectbox, 'paper', 'Kertas', options=['HVS 70','BP 57'])
    mode = draft_widget(a.selectbox, 'mode', 'Mode cetak', options=['Duplex (Bolak-balik)','Simplex (Satu Sisi)'])
    binding = draft_widget(b.selectbox, 'binding', 'Jilid', options=['Soft Cover','Hard Cover'])
    qty = draft_widget(st.number_input, 'qty', 'Jumlah eksemplar', min_value=1, value=1)
    override=None
    if admin:
        with st.expander('Diskon khusus pesanan'):
            if draft_widget(st.checkbox, 'override_enabled', 'Ganti diskon isi otomatis'):
                override = draft_widget(st.number_input, 'override', 'Diskon isi (%)', min_value=0, max_value=100, value=0)
    if uploaded:
        data=uploaded[1]
        try:
            with fitz.open(stream=data,filetype='pdf') as doc:
                if doc.needs_pass: raise ValueError('PDF terkunci. Unggah PDF tanpa kata sandi.')
                total=len(doc)
            if total<1: raise ValueError('PDF tidak memiliki halaman.')
            st.caption(f'{total} halaman PDF')
            if method=='Analisis warna otomatis':
                with st.expander('Pengaturan deteksi'):
                    force = draft_widget(st.checkbox, 'force_bw', 'Cetak seluruh halaman sebagai BW', help='Warna asli PDF tetap ada. Aktifkan grayscale pada mesin cetak bila diperlukan.')
                    sensitivity = draft_widget(st.slider, 'sensitivity', 'Batas kontras warna', min_value=5, max_value=50, value=25)
                    pct = draft_widget(st.slider, 'pct', 'Area warna minimum (%)', min_value=0.01, max_value=5.0, value=0.1)
                if st.button('Analisis PDF',type='primary'):
                    with st.spinner('Memeriksa halaman…'):
                        st.session_state['analysis']=(hashlib.sha256(data).hexdigest(),mode,force,sensitivity,pct,process_and_split_pdf(data,force,sensitivity,pct,mode,total))
                saved=st.session_state.get('analysis')
                if saved and saved[:5]==(hashlib.sha256(data).hexdigest(),mode,force,sensitivity,pct): colors,blacks,cb,bb,_=saved[5]
                else: st.info('Tekan Analisis PDF untuk memperbarui hasil.'); colors=[];blacks=[]
            else:
                if roman > total:
                    raise ValueError(f'Jumlah preliminaries melebihi {total} halaman PDF.')
                pair = draft_widget(st.checkbox, 'pair', 'Sertakan pasangan duplex', value=True, disabled=mode.startswith('Simplex'))
                colors,_,errors,_=parse_page_input(selection,total,roman)
                if errors: st.error(' • '.join(errors)); st.stop()
                if colors:
                    if pair and mode.startswith('Duplex'): colors=add_duplex_pairs(colors,total)
                    colors,blacks,cb,bb=split_pdf_by_pages(data,tuple(colors),total)
            color,bw=len(colors),len(blacks)
        except (ValueError,RuntimeError) as e: st.error(str(e)); st.stop()
    st.subheader('3. Periksa halaman')
    st.write(f'{color} halaman warna · {bw} halaman BW')
    if colors or blacks:
        with st.expander('Rincian nomor halaman PDF'):
            st.write('Warna:',', '.join(map(str,colors)) or 'Tidak ada'); st.write('BW:',', '.join(map(str,blacks)) or 'Tidak ada')
with right:
    st.subheader('4. Ringkasan biaya')
    if color+bw==0: st.info('Lengkapi naskah untuk melihat biaya dan mengunduh hasil.')
    else:
        r=calculate(config,size,paper,mode,binding,qty,color,bw,override)
        st.metric('Total pesanan',rp(r['total'])); st.metric('Harga per eksemplar',rp(r['unit']))
        st.write(f"DP {config['dp']}%: **{rp(r['dp'])}**")
        st.write(f"Diskon isi: {r['discount']}% · finishing: {r['finishing_discount']}%")
        st.caption(f"Pembanding seluruh halaman warna: {rp(r['full'])}. Selisih: {rp(r['full']-r['total'])}. Spesifikasi dan diskon sama.")
        receipt=f"LITNUS PRINTING\nESTIMASI BIAYA\n{title}\nTarif versi {version}\n{size} | {paper} | {mode} | {binding}\n{color} halaman warna + {bw} BW\n{qty} eksemplar\nHarga/eks: {rp(r['unit'])}\nTotal: {rp(r['total'])}\nDP {config['dp']}%: {rp(r['dp'])}\nDiskon isi {r['discount']}% | finishing {r['finishing_discount']}%\nHalaman PDF warna: {colors}\nHalaman PDF BW: {blacks}\nDokumen estimasi, bukan bukti pembayaran."
        st.download_button('Unduh estimasi biaya',receipt,'Estimasi_Litnus.txt','text/plain',use_container_width=True)
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

Silakan transfer sesuai pilihan pembayaran.

Mandiri
144-00-2306065-7
a/n PT Literasi Nusantara Abadi Grup

BCA
117-737-3737
a/n PT Literasi Nusantara Abadi Grup

Mohon kirim bukti transfer setelah pembayaran.
Terima kasih.
"""
        st.download_button(
            'Unduh nota tagihan (TXT)',
            invoice,
            'Nota_Tagihan_Litnus.txt',
            'text/plain; charset=utf-8',
            use_container_width=True,
        )
        if cb: st.download_button('Unduh PDF warna',cb,'Litnus_Warna.pdf','application/pdf',use_container_width=True)
        if bb: st.download_button('Unduh PDF BW',bb,'Litnus_BW.pdf','application/pdf',use_container_width=True)
        with st.expander('Rincian tarif'):
            st.write({'Warna/hlm':rp(r['color_rate']),'BW/hlm':rp(r['bw_rate']),'Finishing/eks':rp(r['finishing'])})
