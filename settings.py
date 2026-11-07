import json
import psycopg
from psycopg.types.json import Jsonb
import streamlit as st
from engine import PRICING_MATRIX

DEFAULT = {
    'prices': PRICING_MATRIX,
    'simplex': 1.5,
    'hardcover': 1.5,
    'dp': 50,
    'tiers': [{'minimum': n, 'discount': min((i + 1) * 4, 32)} for i, n in enumerate([4, 10, 20, 30, 50, 100, 200, 500, 1000])],
    'finishing_step': 5,
    'finishing_discount': 2,
    'finishing_cap': 40,
}

def connect():
    return psycopg.connect(st.secrets['database']['url'], connect_timeout=10)

@st.cache_resource(ttl=3600)
def ensure_schema():
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS litnus_settings (id integer PRIMARY KEY, version integer NOT NULL, data jsonb NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS litnus_history (id bigserial PRIMARY KEY, created_at timestamptz DEFAULT now(), actor text NOT NULL, reason text NOT NULL, old_data jsonb NOT NULL, new_data jsonb NOT NULL)')
        c.execute('INSERT INTO litnus_settings VALUES (1,1,%s) ON CONFLICT DO NOTHING', (Jsonb(DEFAULT),))
    return True

def setup():
    return ensure_schema()

@st.cache_data(ttl=120, show_spinner=False)
def read_cached():
    with connect() as c:
        return c.execute('SELECT version,data FROM litnus_settings WHERE id=1').fetchone()

def read():
    return read_cached()

def save(data, version, reason):
    if not st.user.is_logged_in or st.user.get('email') not in st.secrets.get('admin_emails', []):
        raise PermissionError('Akses admin diperlukan.')
    validate(data)
    with connect() as c:
        old = c.execute('SELECT version,data FROM litnus_settings WHERE id=1 FOR UPDATE').fetchone()
        if old[0] != version:
            read_cached.clear()
            raise ValueError('Harga sudah diubah admin lain. Muat ulang sebelum menyimpan.')
        c.execute('UPDATE litnus_settings SET version=version+1,data=%s WHERE id=1', (Jsonb(data),))
        c.execute('INSERT INTO litnus_history(actor,reason,old_data,new_data) VALUES (%s,%s,%s,%s)', (st.user['email'], reason, Jsonb(old[1]), Jsonb(data)))
    read_cached.clear()

def validate(d):
    if not 0 <= d['dp'] <= 100:
        raise ValueError('DP harus 0–100%.')
    if d['simplex'] <= 0 or d['hardcover'] <= 0:
        raise ValueError('Pengali harus positif.')
    if d['finishing_step'] < 1:
        raise ValueError('Interval finishing minimal 1.')
    for key in ['finishing_discount', 'finishing_cap']:
        if not 0 <= d[key] <= 100:
            raise ValueError('Diskon harus 0–100%.')
    for p in d['prices'].values():
        if p['base_finishing_soft'] < 0:
            raise ValueError('Tarif tidak boleh negatif.')
        for paper in ['HVS 70', 'BP 57']:
            if any(v < 0 for v in p[paper].values()):
                raise ValueError('Tarif tidak boleh negatif.')
    mins = []
    for t in d['tiers']:
        if t['minimum'] < 1 or int(t['minimum']) != t['minimum'] or not 0 <= t['discount'] <= 100:
            raise ValueError('Jenjang diskon tidak valid.')
        mins.append(t['minimum'])
    if len(set(mins)) != len(mins):
        raise ValueError('Minimum jumlah tidak boleh duplikat.')

def calculate(
    d,
    size,
    paper,
    mode,
    binding,
    qty,
    color,
    bw,
    override=None,
    full_color_complexity_mode=False,
    page_toner_pcts=None,
    color_pages_list=None,
):
    p = d['prices'][size]
    factor = d['simplex'] if mode == 'Simplex (Satu Sisi)' else 1
    discount = max((t['discount'] for t in sorted(d['tiers'], key=lambda t: t['minimum']) if qty >= t['minimum']), default=0)
    if override is not None:
        discount = override

    # cr = Harga 100% Warna Blok (setelah diskon oplah), br = Harga Dasar BW (setelah diskon oplah)
    cr = int(int(p[paper]['warna'] * factor) * (1 - discount / 100))
    br = int(int(p[paper]['bw'] * factor) * (1 - discount / 100))

    f = int(p['base_finishing_soft'] * (d['hardcover'] if binding == 'Hard Cover' else 1))
    fd = min((qty // d['finishing_step']) * d['finishing_discount'], d['finishing_cap'])
    f -= int(f * fd / 100)

    total_pages = color + bw
    avg_toner_pct = 0.0
    toner_savings_per_book = 0

    if full_color_complexity_mode and page_toner_pcts and total_pages > 0:
        # Mode Full Colour / Kompleksitas Warna:
        # Tiap halaman dihitung proporsional berdasarkan % toner warna yang dipakai dibanding harga 100% warna blok.
        # Rumus per halaman: Harga_Halaman = br + (toner_pct / 100.0) * (cr - br)
        # (Atau cr dikurangi proporsi warna yang tidak terpakai, dengan batas minimum br).
        toner_margin_100 = max(0, cr - br)
        content_cost = 0.0
        toner_sum = 0.0

        for pno in range(1, total_pages + 1):
            pct = float(page_toner_pcts.get(pno, 0.0))
            pct = max(0.0, min(100.0, pct))
            toner_sum += pct
            page_price = br + (pct / 100.0) * toner_margin_100
            content_cost += page_price

        content_cost_int = int(round(content_cost))
        avg_toner_pct = round(toner_sum / total_pages, 2)
        full_block_content = total_pages * cr
        toner_savings_per_book = max(0, full_block_content - content_cost_int)
        unit = content_cost_int + f
    else:
        unit = color * cr + bw * br + f

    return dict(
        unit=unit,
        total=unit * qty,
        dp=int(unit * qty * d['dp'] / 100),
        discount=discount,
        finishing_discount=fd,
        finishing=f,
        color_rate=cr,
        bw_rate=br,
        full=((color + bw) * cr + f) * qty,
        avg_toner_pct=avg_toner_pct,
        toner_savings_total=toner_savings_per_book * qty,
        toner_savings_unit=toner_savings_per_book,
    )
