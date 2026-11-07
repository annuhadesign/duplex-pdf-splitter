import copy
import json
import hashlib
import fitz
import streamlit as st
from engine import parse_page_input, add_duplex_pairs, split_pdf_by_pages, process_and_split_pdf, format_rupiah as rp
from settings import DEFAULT, setup, read, save, calculate, validate

st.set_page_config(page_title='Litnus • Studio Cetak',page_icon='📚',layout='wide')
st.markdown('''<style>
.block-container{max-width:1200px;padding-top:2rem}h1{letter-spacing:-.04em} .intro{padding:24px 28px;background:linear-gradient(120deg,#102e65,#08162f);border:1px solid #24558a;border-radius:16px;margin-bottom:24px}.intro p{color:#b6d6f2;margin:0}.intro h1{color:#f4f8ff;margin:0 0 8px}.trail{color:#91c9ef;padding:12px 0 22px;font-size:14px}div[data-testid="stMetric"]{background:#102341;padding:18px;border-radius:12px}button:focus-visible,input:focus-visible{outline:3px solid #ffce70!important}button{min-height:44px} .stDownloadButton button{border-color:#77caff} @media(max-width:600px){.block-container{padding:1rem}.intro{padding:18px}.intro h1{font-size:30px}}
</style><div class="intro"><h1>Studio Cetak Litnus</h1><p>Dari naskah hingga siap produksi.</p></div>''',unsafe_allow_html=True)
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
with st.sidebar:
    st.title('Litnus Printing')
    screen=st.radio('Ruang kerja',['Produksi','Admin'])
    st.caption(f'Versi tarif: {version or "bawaan"}')
    if logged_in: st.button('Keluar',on_click=st.logout)
if screen=='Admin':
    if not admin:
        st.subheader('Masuk sebagai admin')
        st.write('Gunakan akun yang tercantum pada daftar admin.')
        if 'auth' in secrets:
            if st.button('Masuk dengan akun Google'): st.login()
        else: st.info('Login belum dikonfigurasi. Ikuti README untuk mengaktifkannya.')
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

st.markdown('<div class="trail">01 Naskah &nbsp; / &nbsp; 02 Spesifikasi &nbsp; / &nbsp; 03 Periksa &nbsp; / &nbsp; 04 Siap cetak</div>',unsafe_allow_html=True)
left,right=st.columns([1.7,1],gap='large')
with left:
    st.subheader('1. Naskah')
    method=st.selectbox('Cara input',['Analisis warna otomatis','Pilih halaman manual','Jumlah halaman saja'])
    title=st.text_input('Judul buku',value='Pesanan Litnus')
    uploaded=None; color=bw=0; cb=bb=None; colors=[]; blacks=[]
    if method!='Jumlah halaman saja': uploaded=st.file_uploader('Unggah PDF isi buku',type='pdf')
    else:
        a,b=st.columns(2); color=a.number_input('Halaman warna',0,value=0); bw=b.number_input('Halaman BW',0,value=0)
    st.subheader('2. Spesifikasi')
    a,b=st.columns(2)
    size=a.selectbox('Ukuran',list(config['prices'])); paper=b.selectbox('Kertas',['HVS 70','BP 57'])
