import html

import fitz
import streamlit as st

from preflight import compare_pdf, fit_score, inspect_pdf, page_ranges, report_text, target_dimensions
from print_documents import rupiah, with_adjustment

MENU_LABELS = {'Kalkulator Cepat': 'Estimasi Manual', 'Deteksi Warna PDF': 'Analisis PDF'}
MENU_HELP = {
    'Kalkulator Cepat': 'Hitung biaya dari jumlah halaman yang kamu masukkan. Cocok sebelum PDF tersedia; ukuran dan kesiapan berkas belum diperiksa.',
    'Deteksi Warna PDF': 'Periksa ukuran setiap halaman, batas potong dan metadata bleed; lalu jalankan deteksi warna untuk menghitung biaya dari PDF.',
    'Pilah Halaman PDF': 'Pilih halaman warna memakai nomor Romawi atau Arab, sertakan pasangan duplex, lalu unduh PDF warna dan BW secara terpisah.',
    'Admin Tarif': 'Atur tarif, diskon, finishing dan persentase DP. Perubahan hanya dapat disimpan oleh admin yang terdaftar.',
    'Ganti Sesi': 'Gunakan nama tamu atau masuk dengan akun Google yang terdaftar.',
}

CSS = '''<style>
.page-title-line{display:flex;gap:12px;align-items:center;flex-wrap:wrap;position:relative}
.mode-info{position:relative;display:inline-block;vertical-align:middle;font:500 13px/1.5 sans-serif}
.mode-info>button{border:1px solid #7eaaa6;background:#edf8f5;color:#0b6965;border-radius:50%;width:30px;height:30px;font:700 17px Georgia;cursor:help;display:grid;place-items:center}
.mode-info>button:focus-visible{outline:3px solid #bb8b2f;outline-offset:3px}
.mode-info .tip{visibility:hidden;opacity:0;position:absolute;left:0;top:36px;width:280px;max-width:70vw;background:#174d49;color:#fff;padding:13px 15px;border-radius:13px;box-shadow:0 9px 25px #113f4833;z-index:100;transition:opacity .12s}
.mode-info:hover .tip,.mode-info:focus-within .tip{visibility:visible;opacity:1}
.st-key-card_preflight,.st-key-card_comparison,.st-key-card_documents{background:rgba(238,247,245,.72);border:1.5px solid #ffffffd1;border-radius:24px;padding:1.35rem 1.6rem;box-shadow:0 12px 26px -8px #113c3a18;margin-bottom:1.15rem;min-width:0;max-width:100%;box-sizing:border-box}
.pf-status{padding:14px 16px;border:1px solid #b5cebf;background:#e3f4eb;border-radius:15px;color:#245a42;margin-bottom:12px}.pf-status.review{background:#fff4d9;color:#70551a;border-color:#e1ce9e}
.pf-status strong{display:block;font-size:1.03rem}.pf-status small{display:block;margin-top:4px;font-size:.8rem}
.pf-summary{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.pf-summary span{border:1px solid #c3d8d4;border-radius:10px;background:#ffffff80;padding:7px 10px;font-size:.78rem}
.pf-group{padding:12px 0;border-bottom:1px solid #c9dbd6;font-size:.85rem;overflow-wrap:anywhere}.pf-group b{color:#175c58}.pf-group small{display:block;color:#54706b;line-height:1.6}
.pf-scope{font-size:.77rem;color:#56706c;line-height:1.65;margin:12px 0}
.comparison-mobile{display:none}.comparison-option{padding:12px;border:1px solid #c3d8d4;border-radius:14px;background:#ffffff80;margin-bottom:8px;font-size:.85rem}.comparison-option small{display:block;color:#54706b;margin:5px 0}.comparison-option b{color:#095e5c}
@media(max-width:900px){.st-key-comparison_table{display:none!important}.comparison-mobile{display:block}.st-key-card_preflight,.st-key-card_comparison,.st-key-card_documents{padding:1.1rem!important;border-radius:20px!important}.mode-info{position:static}.mode-info .tip{left:0;right:auto;top:100%;width:280px;max-width:75vw}}
</style>'''


def info_html(screen):
    text = html.escape(MENU_HELP.get(screen, ''))
    return (f'<span class="mode-info"><button type="button" aria-label="Informasi mode" '
            f'aria-describedby="mode-tip">i</button><span class="tip" role="tooltip" id="mode-tip">{text}</span></span>')


@st.cache_data(show_spinner=False, max_entries=6)
def inspect_cached(data):
    return inspect_pdf(data)


@st.cache_data(show_spinner=False, max_entries=12)
def page_preview(data, number):
    with fitz.open(stream=data, filetype='pdf') as doc:
        page = doc[number - 1]
        factor = min(1.5, 900 / max(page.rect.width, page.rect.height))
        return page.get_pixmap(matrix=fitz.Matrix(factor, factor), alpha=False).tobytes('png')


def render_report(result, data, filename, size, key):
    with st.container(key='card_preflight'):
        st.subheader('Pemeriksaan berkas')
        review = bool(result['flagged'])
        st.markdown(f'<div class="pf-status {"review" if review else ""}"><strong>{html.escape(result["status"])}</strong>'
                    '<small>Pemeriksaan awal; persetujuan naik cetak tetap dari tim produksi.</small></div>', unsafe_allow_html=True)
        target = result['target']
        target_text = f'{target[0]:g} × {target[1]:g} mm' if target else 'dimensi belum dikenali'
        st.caption(f'Target: {size} · {target_text} · toleransi ukuran ±0,5 mm')
        st.markdown(f'<div class="pf-summary"><span>{result["count"]} halaman diperiksa</span>'
                    f'<span>{len(result["groups"])} kelompok ukuran/batas</span>'
                    f'<span>{result["matching"]} sesuai target</span></div>', unsafe_allow_html=True)
        for group in result['groups']:
            numbers = page_ranges(group['pages'])
            compact = numbers if len(numbers) < 180 else numbers[:177] + '…'
            st.markdown(f'<div class="pf-group"><b>{group["name"]} · {group["width"]:g} × {group["height"]:g} mm</b>'
                        f' · {len(group["pages"])} hlm<small>{group["orientation"]} · acuan {group["source"]}'
                        f' · halaman {compact}</small></div>', unsafe_allow_html=True)
        if result['reasons']:
            for reason, count in result['reasons'].items():
                st.write(f'• {reason} — **{count} halaman**')
        st.caption('BleedBox yang tersedia hanya menunjukkan area yang dinyatakan. Isi gambar sampai tepi, font, DPI efektif, profil warna, margin aman dan imposition belum diverifikasi.')
        if result['required_bleed'] == 0:
            st.caption('Bleed tidak diwajibkan pada pesanan ini. Aktifkan “Cetak isi sampai tepi” bila desain menyentuh batas potong.')
        with st.expander('Rincian halaman & pratinjau'):
            flagged_only = st.checkbox('Hanya halaman dengan catatan', value=True, key=f'flagged:{key}')
            pages = [p for p in result['pages'] if p['issues']] if flagged_only else result['pages']
            st.dataframe([{'Hlm': p['number'], 'Ukuran': p['name'], 'Lebar mm': p['width'], 'Tinggi mm': p['height'],
                           'Acuan': p['source'], 'Rotasi °': p['rotation'], 'Skala fit %': round(p['scale'] * 100, 2) if p['scale'] else None,
                           'Bleed min mm': min(p['bleed'].values()) if p['bleed'] else None,
                           'Catatan': '; '.join(p['issues']) or 'Ukuran sesuai'} for p in pages],
                         use_container_width=True, hide_index=True)
            number = st.number_input('Nomor halaman PDF', min_value=1, max_value=result['count'], value=1, key=f'preview-page:{key}')
            selected = result['pages'][number - 1]
            if selected['scale']:
                pad_x, pad_y = selected['padding']
                st.write(f'Fit proporsional ke target: **{selected["scale"] * 100:.2f}%**. '
                         f'Sisa ruang per sisi: horizontal {pad_x:.2f} mm, vertikal {pad_y:.2f} mm.')
                if selected['scale'] < .999:
                    st.caption('Teks dan gambar ikut mengecil. Periksa keterbacaan sebelum memakai ukuran ini.')
                elif selected['scale'] > 1.001:
                    st.caption('Pembesaran dapat menurunkan DPI efektif gambar. Periksa kualitas cetaknya.')
            if selected['bleed']:
                st.write('Batas bleed sumber: ' + ' · '.join(f'{side} {value:g} mm' for side, value in selected['bleed'].items()))
                if selected['bleed_fit']:
                    st.caption(f'Perkiraan bleed minimum setelah fit terpusat: {min(selected["bleed_fit"].values()):.2f} mm. Ini simulasi batas, bukan pemeriksaan isi gambar.')
            if st.checkbox('Tampilkan gambar halaman', key=f'show-preview:{key}'):
                try:
                    st.image(page_preview(data, number), caption=f'Halaman PDF {number} · tampilan CropBox asli', use_container_width=True)
                except (RuntimeError, ValueError) as exc:
                    st.warning(f'Pratinjau belum dapat dirender: {exc}')
        st.download_button('Unduh laporan pemeriksaan', report_text(result, filename, size),
                           'Pemeriksaan_PDF.txt', 'text/plain; charset=utf-8', key=f'report:{key}', use_container_width=True)


def choose_size(method, label):
    st.session_state[f'draft:{method}:size'] = label
    st.session_state[f'widget:draft:{method}:size'] = label


def render_comparison(report, sizes, orientation, current_size, calculator, fee, dp, method):
    with st.container(key='card_comparison'):
        st.subheader('Bandingkan ukuran & biaya')
        rows, options = [], []
        for label in sizes:
            target = target_dimensions(label)
            if target and orientation == 'Lanskap':
                target = target[::-1]
            if not target:
                continue
            result = compare_pdf(report, target)
            prices = with_adjustment(calculator(label), fee, dp) if calculator else None
            scales = [p['scale'] * 100 for p in result['pages']]
            rows.append({'Ukuran': label, 'Sesuai': f'{result["matching"]}/{result["count"]}',
                         'Skala fit': f'{min(scales):.1f}–{max(scales):.1f}%',
                         'Cetak/eks': rupiah(prices['unit']) if prices else 'Menunggu analisis warna',
                         'Total': rupiah(prices['total']) if prices else '—'})
            options.append(((-result['matching'], fit_score(report, target)), label))
        if not options:
            st.info('Dimensi ukuran pada tabel tarif belum dikenali; gunakan format “Nama (lebar x tinggi cm)”.')
            return
        best = min(options)[1]
        st.write(f'Paling dekat secara ukuran: **{best}**')
        st.caption('Utamakan jumlah halaman yang sudah cocok, lalu skala dan proporsinya. PDF campuran tetap perlu diperiksa per kelompok; keterbacaan belum dinilai.')
        with st.container(key='comparison_table'):
            st.dataframe(rows, use_container_width=True, hide_index=True)
        cards = ''.join(
            f'<div class="comparison-option"><b>{html.escape(row["Ukuran"])}</b>'
            f'<small>{row["Sesuai"]} halaman sesuai · skala {row["Skala fit"]}</small>'
            f'Cetak/eks: {row["Cetak/eks"]}<br>Total: <b>{row["Total"]}</b></div>'
            for row in rows
        )
        st.markdown(f'<div class="comparison-mobile">{cards}</div>', unsafe_allow_html=True)
        if calculator:
            st.caption(f'Spesifikasi, halaman warna/BW, diskon dan jumlah cetak sama. Total termasuk biaya penyesuaian {rupiah(fee)} sekali/order. Biaya ini belum dibedakan per alternatif ukuran.')
            st.caption('Cakupan warna memakai PDF sumber. Setelah layout atau isi diubah, analisis ulang PDF final untuk memperbarui biaya.')
        options_labels = [label for _, label in options]
        selected = st.selectbox('Ukuran yang akan digunakan', options_labels, index=options_labels.index(best), key=f'compare-size:{method}')
        st.button('Gunakan ukuran ini', disabled=selected == current_size, key=f'apply-size:{method}',
                  on_click=choose_size, args=(method, selected), use_container_width=True)
        st.caption('Mengubah target dan hitungan biaya. PDF asli tidak diubah atau dipotong otomatis.')
