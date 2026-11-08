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
    {
        'author': 'Mohammad Hatta', 'topic': 'Buku dan kebebasan berpikir',
        'original': '',
        'translation': 'Aku rela dipenjara asalkan bersama buku, karena dengan buku aku bebas.',
        'image': 'https://assets.pikiran-rakyat.com/crop/10x98%3A790x604/750x500/photo/2021/11/28/734731773.jpg',
        'source': 'https://balaimedia.kemenbud.go.id/tajuk/antara-buku-dan-rendahnya-minat-baca---zimf0118/',
    },
    {
        'author': 'Pramoedya Ananta Toer', 'topic': 'Menulis dan meninggalkan jejak',
        'original': '',
        'translation': 'Menulis adalah bekerja untuk keabadian.',
        'image': 'https://imagenes.elpais.com/resizer/v2/WLOXV4QN6BYCHQVHVUG7T2GVLY.jpg?auth=e7a843c6b75b17669176f1e8ab30c795a2f9f01a0a7c08ef570b67c118538db1&width=1200',
        'source': 'https://seabadpram.com/home',
    },
    {
        'author': 'Najwa Shihab', 'topic': 'Membaca dan kedewasaan berpikir',
        'original': '',
        'translation': 'Buku mengasah pikiran menjadi tajam dan dewasa.',
        'image': 'https://www.thehandbook.com/cdn-cgi/image/width%3D600%2Cheight%3D600%2Cfit%3Dcover%2Cq%3D80%2Cformat%3Dwebp/https%3A/files.thehandbook.com/uploads/2021/02/aauvwniowwdlt-ae2lurmr80jczlt892ij-ojmcf-kmgs800-c-k-c0x00ffffff-no-rj.jpg',
        'source': 'https://www.ditjenpas.go.id/inilah-catatan-najwa-tentang-buku-dan-penjara-untuk-seluruh-wbp',
    },
    {
        'author': 'Seth Godin', 'topic': 'Pemasaran yang membantu',
        'original': 'Marketing is the generous act of helping someone solve a problem.',
        'translation': 'Pemasaran adalah tindakan murah hati untuk membantu seseorang memecahkan masalah.',
        'image': 'https://f.hubspotusercontent20.net/hubfs/6374779/Imported%20images/seth-godin-hero.jpg',
        'source': 'https://seths.blog/2025/12/building-blocks-of-marketing/',
    },
    {
        'author': 'Peter Drucker', 'topic': 'Memahami kebutuhan pasar',
        'original': 'The aim of marketing is to make selling superfluous.',
        'translation': 'Tujuan pemasaran adalah membuat upaya menjual tidak lagi diperlukan.',
        'image': 'https://thothconsultoria.com.br/uploads/articles/f793f85de6b9f5504666a68fe50d4cef.png',
        'source': 'https://management.co.nz/archive/nzim-daily-drucker-selling-marketing',
    },
    {
        'author': 'Stephen R. Covey', 'topic': 'Mendengarkan pelanggan',
        'original': 'Seek first to understand, then to be understood.',
        'translation': 'Berusahalah memahami terlebih dahulu, baru kemudian dipahami.',
        'image': 'https://proassets.planetadelibros.com.co/usuaris/autores/fotos/7/original/000006359_1_STEPHENR_202306131749.COVEY_202306131749.jpg',
        'source': 'https://www.franklincovey.co.uk/blog/2021/09/21/habit-5-seek-first-to-understand-then-to-be-understood/',
    },
    {
        'author': 'Ann Handley', 'topic': 'Pelanggan sebagai pusat cerita',
        'original': 'Make your customer the hero of your story.',
        'translation': 'Jadikan pelanggan sebagai tokoh utama dalam cerita Anda.',
        'image': 'https://www.marketingprofs.com/events/shakeupb2b/images/headshots/ann-handley.jpg',
        'source': 'https://annhandley.com/make-your-customer-the-hero-of-your-story/',
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


