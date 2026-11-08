from pathlib import Path

import streamlit.components.v1 as components


_quote_card = components.declare_component(
    'litnus_quotes', path=str(Path(__file__).resolve().parent)
)

QUOTES = [
    {
        'author': 'George Bernard Shaw',
        'topic': 'Komunikasi',
        'original': 'The single biggest problem in communication is the illusion that it has taken place.',
        'translation': 'Masalah terbesar dalam komunikasi adalah ilusi bahwa komunikasi telah terjadi.',
        'image': 'https://images.openai.com/static-rsc-4/hiUFHueYtzt5bAnA7BJT5OZcP1QyFS3C2jnu98TZ0U-croWne8D6UKqQH6C7iOdvRXF2olEvT2Lw8JOucLluW5q_gT8HMaq69WbVnWg_fYY_WtuuetxVg8YVpkT8nCsVTT6pD8adQ6wHOwauRl4NCmhoBlaFdqlX3q0Pv9DZ-_U?purpose=inline',
    },
    {
        'author': 'Jorge Luis Borges',
        'topic': 'Buku',
        'original': 'I have always imagined that Paradise will be a kind of library.',
        'translation': 'Saya selalu membayangkan bahwa surga adalah semacam perpustakaan.',
        'image': 'https://images.openai.com/static-rsc-4/xF0S_hdEQGAt10PggXSwbGBYRslbNTOwfeWZ3csFEFY6mzM8ld8S52RZ9EmrQ2HPhApDsqUgISLOEMw3gjseDTsR0bU4PwhaYoMo8oM5OxuSFVAia8NvZ4Wv5GgsWj27T81CdPxv5wWit5e5XbFNmt9mzTEQFr-wtZGc3EtzuGM?purpose=inline',
    },
    {
        'author': 'Benjamin Franklin',
        'topic': 'Menulis dan berkarya',
        'original': 'Either write something worth reading or do something worth writing.',
        'translation': 'Tulislah sesuatu yang layak dibaca, atau lakukan sesuatu yang layak ditulis.',
        'image': 'https://images.openai.com/static-rsc-4/sqlfXCsFgVT5sOqmNGj0zrA0uUSUupBJJw1i3zSvtY0eu0lEo9_mf8a877rXrrPxK6lCYAO6H5HWqNrlPvty1IzXYajtpK8wsrKT1_gNRuY_BbYIBM5bNRAHB5t12DNhUNIbAkQdgrHRnrzwulQNKRp6drbQkWG9salDuiDIsZg?purpose=inline',
    },
]


def render_quote_card(menu):
    starting_slide = {
        'Kalkulator Cepat': 0,
        'Deteksi Warna PDF': 1,
        'Pilah Halaman PDF': 2,
        'Admin Tarif': 0,
        'Ganti Sesi': 1,
    }.get(menu, 0)
    _quote_card(
        quotes=QUOTES,
        menu=menu,
        start_index=starting_slide,
        interval_ms=12000,
        key=f'litnus_quotes:{menu}',
        default=None,
    )
