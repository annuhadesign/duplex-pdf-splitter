"""Tampilan HPP. Pemanggil wajib memeriksa hak admin di server."""
import streamlit as st
from print_documents import with_special_discount
from engine import format_rupiah as rp
from production_costs import (PAPERS, PAPER_COSTS, get_costs,
                              calculate_production)


def edit_costs(config, version):
    costs = get_costs(config)
    st.subheader('3. Matriks HPP Produksi')
    st.caption('Biaya internal per halaman. B5 ISO dan B5 JIS memakai tarif B5 yang sama. '
               'HPP tidak mengikuti diskon atau pengali tarif jual.')
    rows = []
    for size in PAPER_COSTS:
        for paper in PAPERS:
            rate = costs['rates'][size][paper]
            rows.append({'Ukuran': size, 'Kertas': paper, 'Kertas / hlm': rate['paper'],
                         'Toner BW / hlm': rate['bw_toner'], 'Toner warna / hlm': rate['color_toner']})
    edited = st.data_editor(
        rows, key=f'hpp-rates-v2:{version}', hide_index=True, use_container_width=True,
        disabled=['Ukuran', 'Kertas'], num_rows='fixed',
        column_config={
            name: st.column_config.NumberColumn(name, min_value=0, step=1, format='%d', required=required)
            for name, required in [('Kertas / hlm', True), ('Toner BW / hlm', True), ('Toner warna / hlm', False)]
        },
    )
    for row in edited:
        color_toner = row['Toner warna / hlm']
        # Data editor mengembalikan sel numerik kosong sebagai NaN.
        if color_toner is None or color_toner != color_toner:
            color_toner = None
        costs['rates'][row['Ukuran']][row['Kertas']] = {
            'paper': row['Kertas / hlm'], 'bw_toner': row['Toner BW / hlm'],
            'color_toner': color_toner,
        }
    costs['finishing'] = st.number_input(
        'HPP finishing + operasional / eks (Rp)', min_value=0,
        value=int(costs['finishing']), step=500, key=f'hpp-finishing:{version}',
        help='Berlaku sama untuk semua ukuran, jenis jilid, mode cetak, dan jumlah eksemplar.',
    )
    st.caption('HPP isi = halaman BW × (kertas + toner BW) + halaman warna × (kertas + toner warna). '
               'Finishing ditambahkan satu kali per eksemplar, tanpa diskon jumlah cetak.')
    if any(costs['rates'][s][p]['color_toner'] is None for s in PAPER_COSTS for p in PAPERS):
        st.info('Ada tarif toner warna yang kosong. Lengkapi sebelum menghitung pesanan warna. '
                'Tarif awal toner warna HVS 70 dan BP 57 adalah Rp500/halaman.')
    return costs


def render_production(config, size, paper, qty, color, bw, result, *, show_title=True):
    if show_title:
        st.subheader('HPP & Laba Cetak')
    st.caption(f'Internal admin · {size} · {paper} · {qty:,} eks'.replace(',', '.'))
    st.caption('Pendapatan memakai subtotal cetak setelah diskon. HPP dihitung dari halaman cetak akhir; '
               'toner warna tetap per halaman, termasuk saat tarif jual memakai cakupan warna.')
    try:
        hpp = calculate_production(config, size, paper, qty, color, bw,
                                   result.get('subtotal', result['total']))
    except ValueError as exc:
        st.error(f'HPP belum dapat dihitung: {exc}')
        return

    def money(value):
        return 'Belum lengkap' if value is None else rp(value)

    rows = []
    for item in hpp['rows']:
        label = item['label']
        if item['pages'] is not None:
            rate_label = money(item['rate'])
            label += f" ({item['pages']} hlm × {rate_label})"
        rows.append({'Komponen': label, 'Per eks': money(item['unit']), 'Total pesanan': money(item['total'])})
    rows.extend([
        {'Komponen': 'HPP produksi', 'Per eks': money(hpp['unit_cost']), 'Total pesanan': money(hpp['total_cost'])},
        {'Komponen': 'Pendapatan cetak', 'Per eks': money(hpp['sales_unit']), 'Total pesanan': money(hpp['sales_total'])},
        {'Komponen': 'Laba cetak', 'Per eks': money(hpp['profit_unit']), 'Total pesanan': money(hpp['profit_total'])},
    ])
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if not hpp['complete']:
        st.warning('HPP belum lengkap: ' + '; '.join(hpp['missing']) + '. Lengkapi di Admin Tarif.')
    else:
        margin = f"{hpp['margin_pct']:.2f}%" if hpp['margin_pct'] is not None else 'Tidak terdefinisi (pendapatan Rp0)'
        st.markdown(f'**Margin laba cetak: {margin}**')
        if hpp['profit_total'] < 0:
            st.error(f'Harga jual di bawah HPP. Rugi cetak {rp(-hpp["profit_total"])} untuk pesanan ini.')
        elif hpp['profit_total'] == 0:
            st.info('Pendapatan cetak sama dengan HPP (impas).')
    if result.get('adjustment', 0):
        st.caption(f'Biaya penyesuaian berkas {rp(result["adjustment"])} tidak masuk laba cetak '
                   'karena biaya pengerjaannya belum ditentukan.')
    st.caption('Margin = laba cetak ÷ pendapatan cetak × 100%. Ini laba berdasarkan komponen HPP di atas, '
               'bukan laporan laba bersih perusahaan. Angka internal tidak disertakan dalam nota atau estimasi pelanggan.')


def render_simulation(draft, calculate):
    st.markdown('**Simulasi HPP & laba sebelum disimpan**')
    a, b = st.columns(2)
    sizes = list(draft['prices'])
    size = a.selectbox('Ukuran simulasi', sizes, key='hpp-sim-size')
    paper = b.selectbox('Kertas simulasi', list(PAPERS), key='hpp-sim-paper')
    bw = a.number_input('Halaman BW simulasi', min_value=0, value=100, key='hpp-sim-bw')
    color = b.number_input('Halaman warna simulasi', min_value=0, value=0, key='hpp-sim-color')
    mode = a.selectbox('Mode simulasi', ['Duplex (Bolak-balik)', 'Simplex (Satu Sisi)'], key='hpp-sim-mode')
    binding = b.selectbox('Jilid simulasi', ['Soft Cover', 'Hard Cover'], key='hpp-sim-binding')
    qty = st.number_input('Jumlah eks simulasi', min_value=1, value=10, key='hpp-sim-qty')
    if not color + bw:
        st.info('Isi jumlah halaman untuk melihat simulasi HPP dan laba.')
        return
    result = calculate(draft, size, paper, mode, binding, qty, color, bw)
    result = with_special_discount(result, 0, qty, draft['dp'])
    st.caption(f'Harga kalkulasi {rp(result["unit_before_rounding"])}/eks → '
               f'pembulatan ke atas ke ribuan {rp(result["unit"])}/eks.')
    st.caption(f'Diskon isi {result["discount"]}% · diskon finishing jual {result["finishing_discount"]}% · '
               'Simulasi memakai tarif warna penuh. Cakupan warna mengikuti hasil aktual di menu Analisis PDF.')
    render_production(draft, size, paper, qty, color, bw, result, show_title=False)

