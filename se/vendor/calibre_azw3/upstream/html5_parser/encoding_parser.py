#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (absolute_import, division, print_function, unicode_literals)

import string

from .encoding_names import encodings

space_chars = frozenset(("\t", "\n", "\u000C", " ", "\r"))
space_chars_bytes = frozenset(item.encode("ascii") for item in space_chars)
ascii_letters_bytes = frozenset(item.encode("ascii") for item in string.ascii_letters)
ascii_uppercase_bytes = frozenset(item.encode("ascii") for item in string.ascii_uppercase)
spaces_angle_brackets = space_chars_bytes | frozenset((b">", b"<"))
skip1 = space_chars_bytes | frozenset((b"/", ))


PYTHON_NAMES = {
    'iso-8859-8-i': 'iso-8859-8',
    'x-mac-cyrillic': 'mac-cyrillic',
    'macintosh': 'mac-roman',
    'windows-874': 'cp874'}


def codec_name(encoding):
    """Return the python codec name corresponding to an encoding or None if the
    string doesn't correspond to a valid encoding."""
    if isinstance(encoding, bytes):
        try:
            encoding = encoding.decode("ascii")
        except UnicodeDecodeError:
            return
    if encoding:
        encoding = encoding.strip('\t\n\f\r ')
        enc = encodings.get(encoding)
        if enc is not None:
            return PYTHON_NAMES.get(enc, enc)


class EncodingBytes(bytes):
    """String-like object with an associated position and various extra methods
    If the position is ever greater than the string length then an exception is
    raised"""

    def __new__(self, value):
        return bytes.__new__(self, value.lower())

    def __init__(self, value):
        self._position = -1

    def __iter__(self):
        return self

    def __next__(self):
        p = self._position = self._position + 1
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        return self[p:p + 1]

    def next(self):
        # Py2 compat
        return self.__next__()

    def previous(self):
        p = self._position
        if p >= len(self):
            raise StopIteration
        elif p < 0:
            raise TypeError
        self._position = p = p - 1
        return self[p:p + 1]

    @property
    def position(self):
        if self._position >= len(self):
            raise StopIteration
        if self._position >= 0:
            return self._position

    @position.setter
    def position(self, position):
        if self._position >= len(self):
            raise StopIteration
        self._position = position

    @property
    def current_byte(self):
        return self[self.position:self.position + 1]

    def skip(self, chars=space_chars_bytes):
        """Skip past a list of characters"""
        p = self.position  # use property for the error-checking
        while p < len(self):
            c = self[p:p + 1]
            if c not in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def skip_until(self, chars):
        p = self.position
        while p < len(self):
            c = self[p:p + 1]
            if c in chars:
                self._position = p
                return c
            p += 1
        self._position = p
        return None

    def match_bytes(self, bytes):
        """Look for a sequence of bytes at the start of a string. If the bytes
        are found return True and advance the position to the byte after the
        match. Otherwise return False and leave the position alone"""
        p = self.position
        data = self[p:p + len(bytes)]
        rv = data.startswith(bytes)
        if rv:
            self.position += len(bytes)
        return rv

    def jump_to(self, bytes):
        """Look for the next sequence of bytes matching a given sequence. If
        a match is found advance the position to the last byte of the match"""
        new_pos = self[self.position:].find(bytes)
        if new_pos > -1:
            if self._position == -1:
                self._position = 0
            self._position += (new_pos + len(bytes) - 1)
            return True
        else:
            raise StopIteration


class ContentAttrParser(object):

    def __init__(self, data):
        self.data = data

    def parse(self):
        try:
            # Check if the attr name is charset
            # otherwise return
            self.data.jump_to(b"charset")
            self.data.position += 1
            self.data.skip()
            if not self.data.current_byte == b"=":
                # If there is no = sign keep looking for attrs
                return None
            self.data.position += 1
            self.data.skip()
            # Look for an encoding between matching quote marks
            if self.data.current_byte in (b'"', b"'"):
                quote_mark = self.data.current_byte
                self.data.position += 1
                old_pos = self.data.position
                if self.data.jump_to(quote_mark):
                    return self.data[old_pos:self.data.position]
                else:
                    return None
            else:
                # Unquoted value
                old_pos = self.data.position
                try:
                    self.data.skip_until(space_chars_bytes)
                    return self.data[old_pos:self.data.position]
                except StopIteration:
                    # Return the whole remaining value
                    return self.data[old_pos:]
        except StopIteration:
            return None


class EncodingParser(object):
    """Mini parser for detecting character encoding from meta elements"""

    def __init__(self, data):
        """string - the data to work on for encoding detection"""
        self.data = EncodingBytes(data)
        self.encoding = None

    def __call__(self):
        dispatch = ((b"<!--", self.handle_comment), (b"<meta", self.handle_meta),
                    (b"</", self.handle_possible_end_tag), (b"<!", self.handle_other),
                    (b"<?", self.handle_other), (b"<", self.handle_possible_start_tag))
        for byte in self.data:
            keep_parsing = True
            for key, method in dispatch:
                if self.data.match_bytes(key):
                    try:
                        keep_parsing = method()
                        break
                    except StopIteration:
                        keep_parsing = False
                        break
            if not keep_parsing:
                break

        return self.encoding

    def handle_comment(self):
        """Skip over comments"""
        return self.data.jump_to(b"-->")

    def handle_meta(self):
        if self.data.current_byte not in space_chars_bytes:
            # if we have <meta not followed by a space so just keep going
            return True
        # We have a valid meta element we want to search for attributes
        has_pragma = False
        pending_encoding = None
        while True:
            # Try to find the next attribute after the current position
            attr = self.get_attribute()
            if attr is None:
                return True
            if attr[0] == b"http-equiv":
                has_pragma = attr[1] == b"content-type"
                if has_pragma and pending_encoding is not None:
                    self.encoding = pending_encoding
                    return False
            elif attr[0] == b"charset":
                tentative_encoding = attr[1]
                codec = codec_name(tentative_encoding)
                if codec is not None:
                    self.encoding = codec
                    return False
            elif attr[0] == b"content":
                cap = ContentAttrParser(EncodingBytes(attr[1]))
                tentative_encoding = cap.parse()
                if tentative_encoding is not None:
                    codec = codec_name(tentative_encoding)
                    if codec is not None:
                        if has_pragma:
                            self.encoding = codec
                            return False
                        else:
                            pending_encoding = codec

    def handle_possible_start_tag(self):
        return self.handle_possible_tag(False)

    def handle_possible_end_tag(self):
        next(self.data)
        return self.handle_possible_tag(True)

    def handle_possible_tag(self, end_tag):
        data = self.data
        if data.current_byte not in ascii_letters_bytes:
            # If the next byte is not an ascii letter either ignore this
            # fragment (possible start tag case) or treat it according to
            # handle_other
            if end_tag:
                data.previous()
                self.handle_other()
            return True

        c = data.skip_until(spaces_angle_brackets)
        if c == b"<":
            # return to the first step in the overall "two step" algorithm
            # reprocessing the < byte
            data.previous()
        else:
            # Read all attributes
            attr = self.get_attribute()
            while attr is not None:
                attr = self.get_attribute()
        return True

    def handle_other(self):
        return self.data.jump_to(b">")

    def get_attribute(self):
        """Return a name,value pair for the next attribute in the stream,
        if one is found, or None"""
        data = self.data
        # Step 1 (skip chars)
        c = data.skip(skip1)
        assert c is None or len(c) == 1
        # Step 2
        if c in (b">", None):
            return None
        # Step 3
        attr_name = []
        attr_value = []
        # Step 4 attribute name
        while True:
            if c == b"=" and attr_name:
                break
            elif c in space_chars_bytes:
                # Step 6!
                c = data.skip()
                break
            elif c in (b"/", b">"):
                return b"".join(attr_name), b""
            elif c in ascii_uppercase_bytes:
                attr_name.append(c.lower())
            elif c is None:
                return None
            else:
                attr_name.append(c)
            # Step 5
            c = next(data)
        # Step 7
        if c != b"=":
            data.previous()
            return b"".join(attr_name), b""
        # Step 8
        next(data)
        # Step 9
        c = data.skip()
        # Step 10
        if c in (b"'", b'"'):
            # 10.1
            quote_char = c
            while True:
                # 10.2
                c = next(data)
                # 10.3
                if c == quote_char:
                    next(data)
                    return b"".join(attr_name), b"".join(attr_value)
                # 10.4
                elif c in ascii_uppercase_bytes:
                    attr_value.append(c.lower())
                # 10.5
                else:
                    attr_value.append(c)
        elif c == b">":
            return b"".join(attr_name), b""
        elif c in ascii_uppercase_bytes:
            attr_value.append(c.lower())
        elif c is None:
            return None
        else:
            attr_value.append(c)
        # Step 11
        while True:
            c = next(data)
            if c in spaces_angle_brackets:
                return b"".join(attr_name), b"".join(attr_value)
            elif c in ascii_uppercase_bytes:
                attr_value.append(c.lower())
            elif c is None:
                return None
            else:
                attr_value.append(c)
