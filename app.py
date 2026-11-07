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
