"""HPP produksi internal. Tarif jual dan diskon tetap milik settings.py."""
from copy import deepcopy
from math import isfinite
from numbers import Real


COST_KEY = 'production_costs'
PAPERS = ('HVS 70', 'BP 57')
PAPER_COSTS = {
    'Unesco': (28, 37),
    'A5': (24, 30),
    'B5': (42, 47),
    'A4': (44, 60),
}
DEFAULT_COSTS = {
    'finishing': 6000,
    'rates': {
        size: {
            paper: {'paper': prices[i], 'bw_toner': 25,
                    # Data HVS warna belum diberikan, jangan dianggap nol.
                    'color_toner': None if paper == 'HVS 70' else 500}
            for i, paper in enumerate(PAPERS)
        }
        for size, prices in PAPER_COSTS.items()
    },
}


def get_costs(config):
    """Konfigurasi lama tetap bisa dipakai tanpa mengganti tarif jual di Neon."""
    return deepcopy(config.get(COST_KEY, DEFAULT_COSTS))


def size_family(size):
    token = str(size).split()[0].upper() if str(size).split() else ''
    return {'UNESCO': 'Unesco', 'A5': 'A5', 'B5': 'B5', 'A4': 'A4'}.get(token)


def _amount(value, label, optional=False):
    if value is None and optional:
        return
    if (isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value < 0 or int(value) != value):
        raise ValueError(f'{label} harus berupa angka rupiah bulat, minimal 0.')


def validate_costs(costs):
    try:
        _amount(costs['finishing'], 'HPP finishing')
        for size in PAPER_COSTS:
            for paper in PAPERS:
                rate = costs['rates'][size][paper]
                for key, label in [('paper', 'Kertas'), ('bw_toner', 'Toner BW'),
                                   ('color_toner', 'Toner warna')]:
                    _amount(rate[key], f'{label} {size} {paper}', optional=key == 'color_toner')
    except (KeyError, TypeError) as exc:
        raise ValueError('Struktur tabel HPP belum lengkap.') from exc


def calculate_production(config, size, paper, qty, color, bw, sales_total):
    """sales_total: subtotal cetak SETELAH diskon, tanpa jasa penyesuaian.

    HPP warna memakai tarif tetap per halaman, bukan persentase cakupan.
    Jumlah halaman mengikuti klasifikasi cetak akhir (termasuk pasangan duplex).
    """
    for value, label in [(qty, 'Jumlah cetak'), (color, 'Halaman warna'), (bw, 'Halaman BW')]:
        _amount(value, label)
    if qty < 1:
        raise ValueError('Jumlah cetak minimal 1 eksemplar.')
    _amount(sales_total, 'Pendapatan cetak')
    costs = get_costs(config)
    validate_costs(costs)
    family = size_family(size)
    missing = []
    rate = costs['rates'].get(family, {}).get(paper)
    if rate is None:
        missing.append(f'Tarif HPP {size} / {paper}')
    bw_rate = rate['paper'] + rate['bw_toner'] if rate else None
    color_rate = (rate['paper'] + rate['color_toner']
                  if rate and rate['color_toner'] is not None else None)
    if color and rate and color_rate is None:
        missing.append(f'Toner warna {paper} / {family}')

    def line(label, pages, unit_rate):
        unit = 0 if pages == 0 else (pages * unit_rate if unit_rate is not None else None)
        return {'label': label, 'pages': pages, 'rate': unit_rate,
                'unit': unit, 'total': None if unit is None else unit * qty}

    rows = [line('Isi BW', bw, bw_rate), line('Isi warna', color, color_rate)]
    # Tidak ada biaya produksi sebelum halaman dihitung.
    finish = costs['finishing'] if color + bw else 0
    rows.append({'label': 'Finishing + operasional', 'pages': None,
                 'rate': finish, 'unit': finish, 'total': finish * qty})
    complete = not missing
    unit_cost = sum(row['unit'] for row in rows) if complete else None
    total_cost = unit_cost * qty if complete else None
    profit = sales_total - total_cost if complete else None
    return {
        'complete': complete, 'missing': missing, 'rows': rows,
        'unit_cost': unit_cost, 'total_cost': total_cost,
        'sales_total': sales_total, 'sales_unit': sales_total / qty,
        'profit_total': profit, 'profit_unit': profit / qty if complete else None,
        'margin_pct': profit / sales_total * 100 if complete and sales_total else None,
    }
