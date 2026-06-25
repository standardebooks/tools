#!/usr/bin/env python


__license__   = 'GPL v3'
__copyright__ = '2012, Kovid Goyal <kovid@kovidgoyal.net>'
__docformat__ = 'restructuredtext en'

import re
from io import BytesIO
from struct import pack
from typing import Any

from calibre.constants import ismacos, iswindows
from calibre.ebooks.metadata import authors_to_sort_string
from calibre.ebooks.mobi.utils import to_base, utf8_text
from calibre.utils.localization import lang_as_iso639_1
from calibre.utils.standardebooks import deterministic_asin, deterministic_uuid

EXTH_CODES = {
    'creator': 100,
    'publisher': 101,
    'description': 103,
    'identifier': 104,
    'subject': 105,
    'pubdate': 106,
    'review': 107,
    'contributor': 108,
    'rights': 109,
    'type': 111,
    'source': 112,
    'versionnumber': 114,
    'startreading': 116,
    'kf8_header_index': 121,
    'num_of_resources': 125,
    'kf8_thumbnail_uri': 129,
    'kf8_unknown_count': 131,
    'coveroffset': 201,
    'thumboffset': 202,
    'hasfakecover': 203,
    'lastupdatetime': 502,
    'title': 503,
    'language': 524,
    'primary_writing_mode': 525,
    'page_progression_direction': 527,
    'override_kindle_fonts': 528,
}

COLLAPSE_RE = re.compile(r'[ \t\r\n\v]+')


def ebook_identifier(metadata: Any) -> str | None:
    for item in metadata['identifier']:
        identifier = COLLAPSE_RE.sub(' ', str(item)).strip()
        if identifier:
            return identifier
    return None


def build_exth(metadata, prefer_author_sort=False, is_periodical=False,
        share_not_sync=True, cover_offset=None, thumbnail_offset=None,
        start_offset=None, mobi_doctype=2, num_of_resources=None,
        kf8_unknown_count=0, be_kindlegen2=False, kf8_header_index=None,
        page_progression_direction=None, primary_writing_mode=None):
    exth = BytesIO()
    nrecs = 0

    # Write Standard Ebooks identifiers first, matching Kindle's expected metadata order.
    if not is_periodical and not share_not_sync:
        asin = deterministic_asin().encode('ascii')
        for code, value in ((501, b'EBOK'), (504, asin), (113, asin)):
            exth.write(pack(b'>II', code, len(value) + 8))
            exth.write(value)
            nrecs += 1

    for term in metadata:
        if term not in EXTH_CODES:
            continue
        code = EXTH_CODES[term]
        items = metadata[term]
        if term == 'creator':
            if prefer_author_sort:
                creators = [authors_to_sort_string([str(c)]) for c in
                            items]
            else:
                creators = [str(c) for c in items]
            items = creators
        elif term == 'rights':
            try:
                rights = utf8_text(str(metadata.rights[0]))
            except Exception:
                rights = b'Unknown'
            exth.write(pack(b'>II', EXTH_CODES['rights'], len(rights) + 8))
            exth.write(rights)
            nrecs += 1
            continue

        for item in items:
            data = str(item)
            if term != 'description':
                data = COLLAPSE_RE.sub(' ', data)
            if term == 'identifier':
                if data.lower().startswith('urn:isbn:'):
                    data = data[9:]
                elif item.scheme.lower() == 'isbn':
                    pass
                else:
                    continue
            if term == 'language':
                d2 = lang_as_iso639_1(data)
                if d2:
                    data = d2
            data = utf8_text(data)
            exth.write(pack(b'>II', code, len(data) + 8))
            exth.write(data)
            nrecs += 1

    # Write the ebook identifier as the source identifier.
    source_identifier = ebook_identifier(metadata)
    if source_identifier is None:
        source_identifier = 'calibre:' + str(deterministic_uuid())
    source_identifier = source_identifier.encode('utf-8')
    exth.write(pack(b'>II', 112, len(source_identifier) + 8))
    exth.write(source_identifier)
    nrecs += 1

    if is_periodical:
        ids = {0x101:b'NWPR', 0x103:b'MAGZ'}.get(mobi_doctype, None)
        if ids:
            exth.write(pack(b'>II', 501, 12))
            exth.write(ids)
            nrecs += 1

    # Add a publication date entry
    if metadata['date']:
        datestr = str(metadata['date'][0])
    elif metadata['timestamp']:
        datestr = str(metadata['timestamp'][0])

    if datestr is None:
        raise ValueError('missing date or timestamp')

    datestr = datestr.encode('utf-8')
    exth.write(pack(b'>II', EXTH_CODES['pubdate'], len(datestr) + 8))
    exth.write(datestr)
    nrecs += 1
    if is_periodical:
        exth.write(pack(b'>II', EXTH_CODES['lastupdatetime'], len(datestr) + 8))
        exth.write(datestr)
        nrecs += 1

    if be_kindlegen2:
        mv = 200 if iswindows else 202 if ismacos else 201
        vals = {204:mv, 205:2, 206:9, 207:0}
    elif is_periodical:
        # Pretend to be amazon's super secret periodical generator
        vals = {204:201, 205:2, 206:0, 207:101}
    else:
        # Pretend to be kindlegen 1.2
        vals = {204:201, 205:1, 206:2, 207:33307}
    for code, val in vals.items():
        exth.write(pack(b'>III', code, 12, val))
        nrecs += 1
    if be_kindlegen2:
        revnum = b'0730-890adc2'
        exth.write(pack(b'>II', 535, 8 + len(revnum)) + revnum)
        nrecs += 1

    if cover_offset is not None:
        exth.write(pack(b'>III', EXTH_CODES['coveroffset'], 12,
            cover_offset))
        exth.write(pack(b'>III', EXTH_CODES['hasfakecover'], 12, 0))
        nrecs += 2
    if thumbnail_offset is not None:
        exth.write(pack(b'>III', EXTH_CODES['thumboffset'], 12,
            thumbnail_offset))
        thumbnail_uri_str = (f'kindle:embed:{to_base(thumbnail_offset, base=32, min_num_digits=4)}').encode('utf-8')
        exth.write(pack(b'>II', EXTH_CODES['kf8_thumbnail_uri'], len(thumbnail_uri_str) + 8))
        exth.write(thumbnail_uri_str)
        nrecs += 2

    if start_offset is not None:
        try:
            len(start_offset)
        except TypeError:
            start_offset = [start_offset]
        for so in start_offset:
            if so is not None:
                exth.write(pack(b'>III', EXTH_CODES['startreading'], 12,
                    so))
                nrecs += 1

    if kf8_header_index is not None:
        exth.write(pack(b'>III', EXTH_CODES['kf8_header_index'], 12,
            kf8_header_index))
        nrecs += 1

    if num_of_resources is not None:
        exth.write(pack(b'>III', EXTH_CODES['num_of_resources'], 12,
            num_of_resources))
        nrecs += 1

    if kf8_unknown_count is not None:
        exth.write(pack(b'>III', EXTH_CODES['kf8_unknown_count'], 12,
            kf8_unknown_count))
        nrecs += 1

    if primary_writing_mode:
        pwm = primary_writing_mode.encode('utf-8')
        exth.write(pack(b'>II', EXTH_CODES['primary_writing_mode'], len(pwm) + 8))
        exth.write(pwm)
        nrecs += 1

    if page_progression_direction in {'rtl', 'ltr', 'default'}:
        ppd = page_progression_direction.encode('ascii')
        exth.write(pack(b'>II', EXTH_CODES['page_progression_direction'], len(ppd) + 8))
        exth.write(ppd)
        nrecs += 1

    exth.write(pack(b'>II', EXTH_CODES['override_kindle_fonts'], len(b'true') + 8))
    exth.write(b'true')
    nrecs += 1

    exth = exth.getvalue()
    trail = len(exth) % 4
    pad = b'\0' * (4 - trail)  # Always pad w/ at least 1 byte
    exth = [b'EXTH', pack(b'>II', len(exth) + 12, nrecs), exth, pad]
    return b''.join(exth)
