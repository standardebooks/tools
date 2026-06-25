#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

from lxml.etree import _Comment

if sys.version_info.major < 3:
    from xml.etree.cElementTree import Element, SubElement, ElementTree, Comment, register_namespace
else:
    from xml.etree.ElementTree import Element, SubElement, ElementTree, Comment, register_namespace


register_namespace('svg', "http://www.w3.org/2000/svg")
register_namespace('xlink',  "http://www.w3.org/1999/xlink")


def convert_elem(src, parent=None):
    if parent is None:
        ans = Element(src.tag, dict(src.items()))
    else:
        ans = SubElement(parent, src.tag, dict(src.items()))
    return ans


def adapt(src_tree, return_root=True, **kw):
    src_root = src_tree.getroot()
    dest_root = convert_elem(src_root)
    stack = [(src_root, dest_root)]
    while stack:
        src, dest = stack.pop()
        for src_child in src.iterchildren():
            if isinstance(src_child, _Comment):
                dest_child = Comment(src_child.text)
                dest_child.tail = src_child.tail
                dest.append(dest_child)
            else:
                dest_child = convert_elem(src_child, dest)
                dest_child.text, dest_child.tail = src_child.text, src_child.tail
                stack.append((src_child, dest_child))
    return dest_root if return_root else ElementTree(dest_root)
