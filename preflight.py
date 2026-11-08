"""Read PDF page geometry without changing the uploaded document."""
import math
import re
from collections import Counter

import fitz

MM_PER_PT = 25.4 / 72
TOLERANCE_MM = 0.5
STANDARD_SIZES = {
    'A3': (297, 420), 'A4': (210, 297), 'A5': (148, 210),
    'A6': (105, 148), 'B5 ISO': (176, 250), 'B5 JIS': (182, 257),
    'Unesco': (155, 230), 'Letter': (215.9, 279.4), 'Legal': (215.9, 355.6),
}


def target_dimensions(label):
    match = re.search(r'\(([\d.,]+)\s*[x×]\s*([\d.,]+)\s*(cm|mm)\)', label, re.I)
    if not match:
        return None
    unit = 10 if match[3].lower() == 'cm' else 1
    return tuple(float(match[i].replace(',', '.')) * unit for i in (1, 2))


def _entry(doc, xref, key, inherit=False):
    seen = set()
    while xref and xref not in seen:
        seen.add(xref)
        kind, value = doc.xref_get_key(xref, key)
        if kind != 'null':
            if kind == 'xref':
                value = doc.xref_object(int(value.split()[0]), compressed=True)
            return value
        if not inherit:
            break
        kind, parent = doc.xref_get_key(xref, 'Parent')
        xref = int(parent.split()[0]) if kind == 'xref' else 0
    return None


def _box(value):
    if value is None:
        return None
    try:
        parts = value.strip().strip('[]').split()
        numbers = tuple(float(n) for n in parts)
        if len(numbers) == 4 and all(math.isfinite(n) for n in numbers):
            if numbers[2] > numbers[0] and numbers[3] > numbers[1]:
                return numbers
    except (ValueError, TypeError):
        pass
    return None


def _contains(outer, inner):
    eps = 0.01
    return (outer[0] <= inner[0] + eps and outer[1] <= inner[1] + eps
            and outer[2] + eps >= inner[2] and outer[3] + eps >= inner[3])


def _dimensions(box, unit, rotation):
    dims = [(box[2] - box[0]) * unit * MM_PER_PT,
            (box[3] - box[1]) * unit * MM_PER_PT]
    if rotation in (90, 270):
        dims.reverse()
    return tuple(round(d, 3) for d in dims)


def size_name(width, height):
    small, large = sorted((width, height))
    for name, (w, h) in STANDARD_SIZES.items():
        if abs(small - w) <= TOLERANCE_MM and abs(large - h) <= TOLERANCE_MM:
            return name
    return 'Kustom'


def page_ranges(pages):
    values = sorted(set(pages))
    groups = []
    for number in values:
        if groups and number == groups[-1][-1] + 1:
            groups[-1].append(number)
        else:
            groups.append([number])
    return ', '.join(str(g[0]) if len(g) == 1 else f'{g[0]}–{g[-1]}' for g in groups)


def inspect_pdf(data):
    with fitz.open(stream=data, filetype='pdf') as doc:
        if doc.needs_pass:
            raise ValueError('PDF terkunci. Unggah salinan yang tidak dilindungi kata sandi.')
        if doc.page_count == 0:
            raise ValueError('PDF tidak memiliki halaman.')
        pages = []
        for page in doc:
            errors = []
            raw = {name: _entry(doc, page.xref, name, name in ('MediaBox', 'CropBox'))
                   for name in ('MediaBox', 'CropBox', 'TrimBox', 'BleedBox')}
            boxes = {name: _box(value) for name, value in raw.items()}
            for name, value in raw.items():
                if value is not None and boxes[name] is None:
                    errors.append(f'{name} tidak valid')
            try:
                unit = float(_entry(doc, page.xref, 'UserUnit') or 1)
                if not math.isfinite(unit) or unit <= 0:
                    raise ValueError()
            except ValueError:
                unit = 1
                errors.append('UserUnit tidak valid')
            media = boxes['MediaBox']
            if media is None:
                media = tuple(page.mediabox)
                errors.append('MediaBox tidak dinyatakan dengan valid')
            crop = boxes['CropBox'] or media
            trim, bleed = boxes['TrimBox'], boxes['BleedBox']
            if not _contains(media, crop):
                errors.append('CropBox melewati MediaBox')
            if trim and not _contains(media, trim):
                errors.append('TrimBox melewati MediaBox')
            if bleed and not _contains(media, bleed):
                errors.append('BleedBox melewati MediaBox')
            if trim and bleed and not _contains(bleed, trim):
                errors.append('BleedBox tidak mencakup TrimBox')
            rotation = page.rotation
            size_box = trim or crop
            w, h = _dimensions(size_box, unit, rotation)
            margins = None
            if trim and bleed and _contains(media, bleed) and _contains(bleed, trim):
                # PDF coordinates: left, bottom, right, top. Rotate to displayed sides.
                left = (trim[0] - bleed[0]) * unit * MM_PER_PT
                bottom = (trim[1] - bleed[1]) * unit * MM_PER_PT
                right = (bleed[2] - trim[2]) * unit * MM_PER_PT
                top = (bleed[3] - trim[3]) * unit * MM_PER_PT
                sides = [top, right, bottom, left]
                shift = (rotation // 90) % 4
                sides = sides[-shift:] + sides[:-shift] if shift else sides
                margins = dict(zip(('atas', 'kanan', 'bawah', 'kiri'), map(lambda n: round(n, 3), sides)))
            pages.append({
                'number': page.number + 1, 'width': w, 'height': h,
                'name': size_name(w, h), 'orientation': 'Lanskap' if w > h else 'Potret',
                'rotation': rotation, 'source': 'TrimBox' if trim else ('CropBox' if boxes['CropBox'] else 'MediaBox'),
                'trim_explicit': trim is not None, 'bleed_explicit': bleed is not None,
                'bleed': margins, 'media_mm': _dimensions(media, unit, rotation),
                'crop_mm': _dimensions(crop, unit, rotation), 'errors': errors,
            })
        return {'pages': pages, 'count': len(pages)}


def compare_pdf(report, target, required_bleed=0):
    checked = []
    for page in report['pages']:
        p = dict(page)
        w, h = p['width'], p['height']
        p['matches'] = bool(target and abs(w - target[0]) <= TOLERANCE_MM and abs(h - target[1]) <= TOLERANCE_MM)
        p['scale'] = min(target[0] / w, target[1] / h) if target else None
        p['padding'] = ((target[0] - w * p['scale']) / 2,
                        (target[1] - h * p['scale']) / 2) if target else None
        p['bleed_fit'] = None
        if p['bleed'] is not None and p['scale']:
            pad_x, pad_y = p['padding']
            p['bleed_fit'] = {side: max(0, margin * p['scale'] - (pad_y if side in ('atas', 'bawah') else pad_x))
                              for side, margin in p['bleed'].items()}
        p['bleed_ok'] = p['bleed_fit'] is not None and min(p['bleed_fit'].values()) + 0.05 >= required_bleed
        issues = list(p['errors'])
        if not target:
            issues.append('Dimensi ukuran target belum tersedia')
        elif not p['matches']:
            issues.append('Ukuran berbeda dari target')
        if not p['trim_explicit']:
            issues.append('Batas potong belum dinyatakan (TrimBox kosong)')
        if required_bleed > 0:
            if p['bleed'] is None:
                issues.append('Bleed belum terverifikasi')
            elif not p['bleed_ok']:
                issues.append(f'Perkiraan bleed setelah fit kurang dari {required_bleed:g} mm')
        p['issues'] = issues
        checked.append(p)
    groups = []
    for p in checked:
        group = next((g for g in groups if g['source'] == p['source']
                      and abs(g['width'] - p['width']) <= TOLERANCE_MM
                      and abs(g['height'] - p['height']) <= TOLERANCE_MM), None)
        if group is None:
            group = {k: p[k] for k in ('width', 'height', 'name', 'source', 'orientation')}
            group['pages'] = []
            groups.append(group)
        group['pages'].append(p['number'])
    reasons = Counter(reason for p in checked for reason in p['issues'])
    if any(p['errors'] for p in checked):
        status = 'Perlu revisi batas halaman'
    elif not target:
        status = 'Target belum dapat dibandingkan'
    elif any(not p['matches'] for p in checked):
        status = 'Perlu penyesuaian ukuran'
    elif any(p['issues'] for p in checked):
        status = 'Perlu konfirmasi produksi'
    else:
        status = 'Lolos pemeriksaan ukuran' + (' & metadata bleed' if required_bleed else '')
    return {'pages': checked, 'groups': groups, 'reasons': dict(reasons), 'status': status,
            'matching': sum(p['matches'] for p in checked), 'count': len(checked),
            'target': target, 'required_bleed': required_bleed,
            'flagged': [p['number'] for p in checked if p['issues']]}


def fit_score(report, target):
    if not target:
        return math.inf
    values = []
    for p in report['pages']:
        scale = min(target[0] / p['width'], target[1] / p['height'])
        unused = 1 - (p['width'] * p['height'] * scale * scale) / (target[0] * target[1])
        values.append(abs(math.log(scale)) + unused)
    return sum(values) / len(values)


def report_text(result, filename, target_label):
    lines = ['LITNUS PRINTLAB — PEMERIKSAAN PDF', f'Berkas: {filename}',
             f'Target: {target_label}', f'Status: {result["status"]}',
             f'Ukuran sesuai: {result["matching"]}/{result["count"]} halaman',
             f'Kebutuhan bleed: {result["required_bleed"]:g} mm/sisi', '']
    for p in result['pages']:
        notes = '; '.join(p['issues']) or 'Ukuran sesuai'
        bleed_note = ('; bleed sumber min ' + f'{min(p["bleed"].values()):.2f} mm') if p['bleed'] else '; bleed belum terverifikasi'
        lines.append(f'Hlm {p["number"]}: {p["name"]} {p["width"]:g} × {p["height"]:g} mm '
                     f'({p["source"]}, rotasi {p["rotation"]}°){bleed_note} — {notes}')
    lines += ['', 'Pemeriksaan awal: ukuran, rotasi, serta metadata batas potong dan bleed.',
              'Isi gambar pada bleed, font, DPI efektif, profil warna, margin aman dan imposition belum diverifikasi.',
              'PDF asli tidak diubah. Tim produksi tetap memeriksa hasil sebelum cetak.']
    return '\n'.join(lines)
