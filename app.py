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
    mode=a.selectbox('Mode cetak',['Duplex (Bolak-balik)','Simplex (Satu Sisi)']); binding=b.selectbox('Jilid',['Soft Cover','Hard Cover'])
    qty=st.number_input('Jumlah eksemplar',1,value=1)
    override=None
    if admin:
        with st.expander('Diskon khusus pesanan'):
            if st.checkbox('Ganti diskon isi otomatis'): override=st.number_input('Diskon isi (%)',0,100,value=0)
    if uploaded:
        data=uploaded.getvalue()
        try:
            with fitz.open(stream=data,filetype='pdf') as doc:
                if doc.needs_pass: raise ValueError('PDF terkunci. Unggah PDF tanpa kata sandi.')
                total=len(doc)
            if total<1: raise ValueError('PDF tidak memiliki halaman.')
            st.caption(f'{total} halaman PDF')
            if method=='Analisis warna otomatis':
                with st.expander('Pengaturan deteksi'):
                    force=st.checkbox('Cetak seluruh halaman sebagai BW')
                    st.caption('File tetap mempertahankan warna asli. Atur grayscale pada mesin saat mencetak BW.')
                    sensitivity=st.slider('Batas kontras warna',5,50,25)
                    pct=st.slider('Area warna minimum (%)',0.01,5.0,0.1)
                if st.button('Analisis PDF',type='primary'):
                    with st.spinner('Memeriksa halaman…'):
                        st.session_state['analysis']=(hashlib.sha256(data).hexdigest(),mode,force,sensitivity,pct,process_and_split_pdf(data,force,sensitivity,pct,mode,total))
                saved=st.session_state.get('analysis')
                if saved and saved[:5]==(hashlib.sha256(data).hexdigest(),mode,force,sensitivity,pct): colors,blacks,cb,bb,_=saved[5]
                else: st.info('Tekan Analisis PDF untuk memperbarui hasil.'); colors=[];blacks=[]
            else:
                roman=st.number_input('Jumlah halaman awal Romawi',0,total,min(12,total))
                selection=st.text_area('Halaman warna','',placeholder='iii-v, 1, 5-9')
                st.caption(f'Arab 1 = PDF {roman+1}. Nomor Romawi mengikuti urutan PDF.')
                pair=st.checkbox('Sertakan pasangan duplex',value=True,disabled=mode.startswith('Simplex'))
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
