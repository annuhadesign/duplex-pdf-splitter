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

def calculate(d, size, paper, mode, binding, qty, color, bw, override=None):
    p = d['prices'][size]
    factor = d['simplex'] if mode == 'Simplex (Satu Sisi)' else 1
    discount = max((t['discount'] for t in sorted(d['tiers'], key=lambda t: t['minimum']) if qty >= t['minimum']), default=0)
    if override is not None:
        discount = override
    cr = int(int(p[paper]['warna'] * factor) * (1 - discount / 100))
    br = int(int(p[paper]['bw'] * factor) * (1 - discount / 100))
    f = int(p['base_finishing_soft'] * (d['hardcover'] if binding == 'Hard Cover' else 1))
    fd = min((qty // d['finishing_step']) * d['finishing_discount'], d['finishing_cap'])
    f -= int(f * fd / 100)
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
    )
