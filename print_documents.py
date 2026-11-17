"""One source of text for preview, clipboard, and TXT exports."""
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def with_special_discount(result, percent, qty, dp_percent):
    """Potong harga lengkap/eks setelah diskon otomatis, sebelum jasa/order.

    Potongan dibulatkan ke rupiah terdekat (setengah dibulatkan naik) per eks.
    Angka diskon otomatis dan cakupan toner tetap menjadi rincian internal.
    """
    try:
        pct = Decimal(str(percent))
    except InvalidOperation as exc:
        raise ValueError('Diskon khusus harus angka 0–100%.') from exc
    if not pct.is_finite() or not 0 <= pct <= 100:
        raise ValueError('Diskon khusus harus angka 0–100%.')
    if isinstance(qty, bool) or qty < 1 or int(qty) != qty:
        raise ValueError('Jumlah cetak harus bilangan bulat minimal 1.')
    value = dict(result)
    before = int(result['unit'])
    cut = int((Decimal(before) * pct / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    value.update(unit_before_special=before, special_discount_pct=float(pct),
                 special_discount_unit=cut, special_discount_total=cut * qty,
                 unit=before - cut, total=(before - cut) * qty)
    value['dp'] = int(value['total'] * dp_percent / 100)
    return value


def rupiah(value):
    return 'Rp ' + f'{round(value):,}'.replace(',', '.')


def with_adjustment(result, fee, dp_percent):
    value = dict(result)
    value['subtotal'] = result['total']
    value['adjustment'] = int(fee)
    value['total'] = result['total'] + int(fee)
    value['dp'] = int(value['total'] * dp_percent / 100)
    return value


def safe_filename(title):
    return re.sub(r'[^\w .-]', '_', title, flags=re.UNICODE).strip(' .')[:100] or 'Cetak'


def build_documents(*, title, customer, version, size, paper, mode, binding,
                    qty, color, bw, result, dp_percent, paid=0, notes='',
                    preflight_status=None, full_color=False):
    r = result
    shared = [f'Pemesan: {customer.strip() or "Belum diisi"}', f'Judul: {title}',
              f'Spesifikasi: {size} | {paper} | {mode} | {binding}',
              f'Isi: {color} halaman warna + {bw} halaman BW', f'Jumlah: {qty} eksemplar']
    if full_color:
        shared += [f'Full Colour proporsional: cakupan rata-rata {r["avg_toner_pct"]}%',
                   f'Tarif efektif isi sebelum diskon khusus: {rupiah(r["avg_page_rate"])}/halaman'
                   if r.get('special_discount_pct', 0) > 0 else
                   f'Tarif efektif: {rupiah(r["avg_page_rate"])}/halaman']
    if r.get('special_discount_pct', 0) > 0:
        shared += [f'Harga cetak/eks: {rupiah(r["unit_before_special"])}',
                   f'Diskon khusus: {r["special_discount_pct"]:g}% ({rupiah(r["special_discount_unit"])}/eks)',
                   f'Harga setelah diskon/eks: {rupiah(r["unit"])}']
    else:
        shared += [f'Harga cetak/eks: {rupiah(r["unit"])}']
    shared += [f'Subtotal cetak: {rupiah(r["subtotal"])}',
               f'Penyesuaian berkas (sekali/order): {rupiah(r["adjustment"])}',
               f'TOTAL: {rupiah(r["total"])}',
               f'DP disarankan {dp_percent}%: {rupiah(r["dp"])}']
    context = [f'Pemeriksaan berkas: {preflight_status or "Belum diperiksa (estimasi manual)"}',
               'Biaya berlaku untuk spesifikasi di atas; ukuran/layout akhir perlu persetujuan produksi.',
               'Ongkir dan pajak tambahan di luar perhitungan ini, jika berlaku.']
    if notes.strip():
        context += [f'Catatan: {notes.strip()}']
    estimate = '\n'.join(['LITNUS PRINTLAB — ESTIMASI BIAYA', '', *shared, '', *context])
    balance = max(0, r['total'] - paid)
    payments = [f'Pembayaran diterima: {rupiah(paid)}', f'Sisa tagihan: {rupiah(balance)}']
    if paid > r['total']:
        payments += [f'Kelebihan pembayaran: {rupiah(paid - r["total"])}']
    invoice = '\n'.join(['LITNUS PRINTLAB — NOTA TAGIHAN CETAK', '', *shared, *payments, '',
                         'Rekening PT Literasi Nusantara Abadi Grup:',
                         'Mandiri: 144-00-2306065-7', 'BCA: 117-737-3737', '', *context])
    return estimate, invoice

