import re
import fitz
import streamlit as st

PRICING_MATRIX = {
    'Unesco (15.5 x 23 cm)': {'base_finishing_soft': 27000, 'HVS 70': {'warna': 600, 'bw': 160}, 'BP 57': {'warna': 650, 'bw': 200}},
    'A5 (14.8 x 21 cm)': {'base_finishing_soft': 25000, 'HVS 70': {'warna': 500, 'bw': 150}, 'BP 57': {'warna': 550, 'bw': 180}},
    'B5 ISO (17.6 x 25 cm)': {'base_finishing_soft': 30000, 'HVS 70': {'warna': 800, 'bw': 180}, 'BP 57': {'warna': 850, 'bw': 210}},
    'B5 JIS (18.2 x 25.7 cm)': {'base_finishing_soft': 31000, 'HVS 70': {'warna': 900, 'bw': 190}, 'BP 57': {'warna': 950, 'bw': 220}},
    'A4 (21 x 29.7 cm)': {'base_finishing_soft': 31000, 'HVS 70': {'warna': 1000, 'bw': 200}, 'BP 57': {'warna': 1100, 'bw': 250}},
}

def format_rupiah(value):
    return f'Rp {int(value):,}'.replace(',', '.')

@st.cache_data(show_spinner=False)
def get_pdf_page_count(file_bytes):
    with fitz.open(stream=file_bytes, filetype='pdf') as doc:
        if doc.needs_pass:
            raise ValueError('PDF terkunci kata sandi. Unggah PDF tanpa kata sandi.')
        total = len(doc)
    if total < 1:
        raise ValueError('PDF tidak memiliki halaman.')
    return total

ROMAN_VALUES = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}

def int_to_roman(number):
    if number <= 0:
        return ''
    pairs = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'), (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'), (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    result = []
    for value, symbol in pairs:
        while number >= value:
            result.append(symbol)
            number -= value
    return ''.join(result)

def roman_to_int(value):
    value = value.upper()
    if not value or not re.fullmatch('[IVXLCDM]+', value):
        return None
    total = 0
    prev = 0
    for char in reversed(value):
        current = ROMAN_VALUES[char]
        if current < prev:
            total -= current
        else:
            total += current
            prev = current
    if int_to_roman(total) != value:
        return None
    return total

def is_roman_token(token):
    return bool(re.fullmatch('[ivxlcdmIVXLCDM]+', token))

def expand_page_token(token):
    token = token.strip()
    if not token:
        return ('error', 'Token kosong')
    if '-' in token:
        parts = token.split('-')
        if len(parts) != 2:
            return ('error', f'Format tidak dikenali: {token}')
        left, right = (parts[0], parts[1])
        if is_roman_token(left) and is_roman_token(right):
            a = roman_to_int(left)
            b = roman_to_int(right)
            if a is None or b is None:
                return ('error', f'Romawi tidak valid: {token}')
            if a > b:
                a, b = (b, a)
            return ('roman', list(range(a, b + 1)))
        if left.isdigit() and right.isdigit():
            a, b = (int(left), int(right))
            if a > b:
                a, b = (b, a)
            return ('arabic', list(range(a, b + 1)))
        return ('error', f'Format range tidak dikenali: {token}')
    if is_roman_token(token):
        value = roman_to_int(token)
        if value is None:
            return ('error', f'Romawi tidak valid: {token}')
        return ('roman', [value])
    if token.isdigit():
        return ('arabic', [int(token)])
    return ('error', f'Format tidak dikenali: {token}')

def parse_page_input(text, total_pages, roman_count):
    if not text or not text.strip():
        return ([], [], [], [])
    if roman_count < 0:
        return ([], [], [], ['Jumlah halaman Romawi tidak valid.'])
    normalized_text = text.replace('–', '-').replace('—', '-')
    normalized_text = re.sub(r'\s*-\s*', '-', normalized_text)
    tokens = [x.strip() for x in re.split(r'[,;\s]+', normalized_text) if x.strip()]
    pdf_pages = set()
    mapping_rows = []
    errors = []
    for token in tokens:
        kind, values = expand_page_token(token)
        if kind == 'error':
            errors.append(values)
            continue
        for value in values:
            if kind == 'roman':
                if value > roman_count:
                    errors.append(f'{token}: halaman Romawi {int_to_roman(value).lower()} melebihi jumlah Romawi ({roman_count}).')
                    continue
                pdf_page = value
                label = int_to_roman(value).lower()
            else:
                pdf_page = roman_count + value
                label = str(value)
                max_arabic = max(0, total_pages - roman_count)
                if value < 1 or value > max_arabic:
                    errors.append(f'{token}: halaman Arab {value} berada di luar rentang 1-{max_arabic}.')
                    continue
            if pdf_page < 1 or pdf_page > total_pages:
                errors.append(f'{token}: menghasilkan PDF halaman {pdf_page}, di luar rentang 1-{total_pages}.')
                continue
            pdf_pages.add(pdf_page)
            mapping_rows.append({'input': label, 'jenis': 'Romawi' if kind == 'roman' else 'Arab', 'nomor': value, 'pdf_page': pdf_page})
    sorted_pages = sorted(pdf_pages)
    unique_mapping = {}
    for row in mapping_rows:
        key = (row['jenis'], row['nomor'], row['pdf_page'])
        unique_mapping[key] = row
    mapping_rows = sorted(unique_mapping.values(), key=lambda x: x['pdf_page'])
    return (sorted_pages, mapping_rows, errors, tokens)

def add_duplex_pairs(selected_pages, total_pages):
    result = set(selected_pages)
    for page in selected_pages:
        if page % 2 == 1:
            pair = page + 1
        else:
            pair = page - 1
        if 1 <= pair <= total_pages:
            result.add(pair)
    return sorted(result)

@st.cache_data(show_spinner='Memisahkan halaman PDF...')
def split_pdf_by_pages(file_bytes, selected_pages, total_pages):
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    selected_set = set(selected_pages)
    doc_selected = fitz.open()
    doc_remaining = fitz.open()
    for page_num in range(total_pages):
        actual_page = page_num + 1
        if actual_page in selected_set:
            doc_selected.insert_pdf(doc, from_page=page_num, to_page=page_num)
        else:
            doc_remaining.insert_pdf(doc, from_page=page_num, to_page=page_num)
    pdf_selected = doc_selected.write() if len(doc_selected) else None
    pdf_remaining = doc_remaining.write() if len(doc_remaining) else None
    doc_selected.close()
    doc_remaining.close()
    doc.close()
    remaining_pages = [p for p in range(1, total_pages + 1) if p not in selected_set]
    return (list(selected_pages), remaining_pages, pdf_selected, pdf_remaining)

@st.cache_data(show_spinner='Menganalisis warna dan memisahkan PDF...')
def process_and_split_pdf(file_bytes, force_bw, sens, min_pct, mode, total_p):
    doc = fitz.open(stream=file_bytes, filetype='pdf')
    pure_color_pages = []
    if not force_bw:
        for page_num in range(total_p):
            page = doc[page_num]
            # DPI 54 + stride 4x lebih cepat tanpa mengurangi akurasi deteksi warna
            pix = page.get_pixmap(dpi=54, colorspace=fitz.csRGB)
            samples = pix.samples
            n = pix.n
            color_pixel_count = 0
            step = n * 4
            sample_count = 0
            for i in range(0, len(samples) - n + 1, step):
                r = samples[i]
                g = samples[i + 1]
                b = samples[i + 2]
                sample_count += 1
                if abs(r - g) > sens or abs(r - b) > sens or abs(g - b) > sens:
                    color_pixel_count += 1
            color_ratio = (color_pixel_count / sample_count * 100) if sample_count else 0
            if color_ratio >= min_pct:
                pure_color_pages.append(page_num + 1)
    final_color_set = set(pure_color_pages)
    if mode == 'Duplex (Bolak-balik)' and (not force_bw):
        final_color_set = set(add_duplex_pairs(sorted(final_color_set), total_p))
    final_color_list = sorted(final_color_set)
    final_bw_list = [p for p in range(1, total_p + 1) if p not in final_color_set]
    doc_warna = fitz.open()
    doc_bw = fitz.open()
    for page_num in range(total_p):
        actual_page = page_num + 1
        if actual_page in final_color_set:
            doc_warna.insert_pdf(doc, from_page=page_num, to_page=page_num)
        else:
            doc_bw.insert_pdf(doc, from_page=page_num, to_page=page_num)
    pdf_warna_bytes = doc_warna.write() if len(doc_warna) else None
    pdf_bw_bytes = doc_bw.write() if len(doc_bw) else None
    doc_warna.close()
    doc_bw.close()
    doc.close()
    return (final_color_list, final_bw_list, pdf_warna_bytes, pdf_bw_bytes, pure_color_pages)
