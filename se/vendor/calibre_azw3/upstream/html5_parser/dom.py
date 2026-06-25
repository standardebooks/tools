#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

from xml.dom.minidom import getDOMImplementation

from lxml.etree import _Comment

impl = getDOMImplementation()

try:
    dict_items = dict.iteritems
except AttributeError:
    dict_items = dict.items


def elem_name_parts(elem):
    tag = elem.tag
    if tag.startswith('{'):
        uri, _, name = tag.rpartition('}')
        if elem.prefix:
            name = elem.prefix + ':' + name
        return uri[1:], name
    return None, tag


def attr_name_parts(name, elem, val):
    if name.startswith('{'):
        uri, _, name = name.rpartition('}')
        uri = uri[1:]
        for prefix, quri in dict_items(elem.nsmap):
            if quri == uri:
                break
        else:
            prefix = None
        if prefix:
            name = prefix + ':' + name
        return uri, name, val
    return None, name, val


def add_namespace_declarations(src, dest):
    changed = src.nsmap
    if changed:
        p = src.getparent()
        if p is not None:
            # Only add namespace declarations different from the parent's
            p = p.nsmap or {}
            changed = {k: v for k, v in dict_items(changed) if v != p.get(k)}
        for prefix, uri in dict_items(changed):
            attr = ('xmlns:' + prefix) if prefix else 'xmlns'
            dest.setAttributeNS('xmlns', attr, uri)


def adapt(source_tree, return_root=True, **kw):
    source_root = source_tree.getroot()
    uri, qname = elem_name_parts(source_root)
    dest_tree = impl.createDocument(uri, qname, None)
    dest_tree.doctype = source_tree.docinfo.doctype
    dest_root = dest_tree.documentElement
    stack = [(source_root, dest_root)]
    while stack:
        src, dest = stack.pop()
        if src.text:
            dest.appendChild(dest_tree.createTextNode(src.text))
        add_namespace_declarations(src, dest)
        for name, val in src.items():
            dest.setAttributeNS(*attr_name_parts(name, src, val))
        for child in src.iterchildren():
            if isinstance(child, _Comment):
                dchild = dest_tree.createComment((child.text or '').replace('--', '—'))
            else:
                dchild = dest_tree.createElementNS(*elem_name_parts(child))
                stack.append((child, dchild))
            dest.appendChild(dchild)
            if child.tail:
                dest.appendChild(dest_tree.createTextNode(child.tail))

    return dest_root if return_root else dest_tree
