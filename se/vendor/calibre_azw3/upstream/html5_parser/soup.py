#!/usr/bin/env python
# vim:fileencoding=utf-8
# License: Apache 2.0 Copyright: 2017, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import absolute_import, division, print_function, unicode_literals

unicode = type('')

cdata_list_attributes = None
universal_cdata_list_attributes = None
empty = ()


def init_bs4_cdata_list_attributes():
    global cdata_list_attributes, universal_cdata_list_attributes
    from bs4.builder import HTMLTreeBuilder
    try:
        attribs = HTMLTreeBuilder.DEFAULT_CDATA_LIST_ATTRIBUTES
    except AttributeError:
        attribs = HTMLTreeBuilder.cdata_list_attributes

    cdata_list_attributes = {k: frozenset(v) for k, v in attribs.items()}
    universal_cdata_list_attributes = cdata_list_attributes['*']


def map_list_attributes(tag_name, name, val):
    if name in universal_cdata_list_attributes:
        return val.split()
    if name in cdata_list_attributes.get(tag_name, empty):
        return val.split()
    return val


def soup_module():
    if soup_module.ans is None:
        try:
            import bs4
            soup_module.ans = bs4
        except ImportError:
            import BeautifulSoup as bs3
            soup_module.ans = bs3
    return soup_module.ans


soup_module.ans = None


def set_soup_module(val):
    soup_module.ans = val


def bs4_fast_append(self, new_child):
    new_child.parent = self
    if self.contents:
        previous_child = self.contents[-1]
        new_child.previous_sibling = previous_child
        previous_child.next_sibling = new_child
        new_child.previous_element = previous_child._last_descendant(False)
    else:
        new_child.previous_sibling = None
        new_child.previous_element = self
    new_child.previous_element.next_element = new_child
    new_child.next_sibling = new_child.next_element = None
    self.contents.append(new_child)


def bs4_new_tag(Tag, soup):

    builder = soup.builder

    def new_tag(name, attrs):
        attrs = {k: map_list_attributes(name, k, v) for k, v in attrs.items()}
        return Tag(soup, name=name, attrs=attrs, builder=builder)

    return new_tag


def bs3_fast_append(self, newChild):
    newChild.parent = self
    if self.contents:
        previousChild = self.contents[-1]
        newChild.previousSibling = previousChild
        previousChild.nextSibling = newChild
        newChild.previous = previousChild._lastRecursiveChild()
    else:
        newChild.previousSibling = None
        newChild.previous = self
    newChild.previous.next = newChild

    newChild.nextSibling = newChild.next_element = None
    self.contents.append(newChild)


def bs3_new_tag(Tag, soup):

    def new_tag(name, attrs):
        ans = Tag(soup, name)
        ans.attrs = attrs.items()
        ans.attrMap = attrs
        return ans

    return new_tag


VOID_ELEMENTS = frozenset(
    'area base br col embed hr img input keygen link menuitem meta param source track wbr'.split())


def is_bs3():
    return soup_module().__version__.startswith('3.')


def init_soup():
    bs = soup_module()
    if is_bs3():
        soup = bs.BeautifulSoup()
        new_tag = bs3_new_tag(bs.Tag, soup)
        append = bs3_fast_append
        soup.isSelfClosing = lambda self, name: name in VOID_ELEMENTS
    else:
        soup = bs.BeautifulSoup('', 'lxml')
        new_tag = bs4_new_tag(bs.Tag, soup)
        append = bs4_fast_append
        if universal_cdata_list_attributes is None:
            init_bs4_cdata_list_attributes()
    return bs, soup, new_tag, bs.Comment, append, bs.NavigableString


def parse(utf8_data, stack_size=16 * 1024, keep_doctype=False, return_root=True):
    from html5_parser import html_parser
    bs, soup, new_tag, Comment, append, NavigableString = init_soup()
    if not isinstance(utf8_data, bytes):
        utf8_data = utf8_data.encode('utf-8')

    def add_doctype(name, public_id, system_id):
        soup.append(bs.Doctype.for_name_and_ids(name, public_id or None, system_id or None))

    dt = add_doctype if keep_doctype and hasattr(bs, 'Doctype') else None
    root = html_parser.parse_and_build(
        utf8_data, new_tag, Comment, NavigableString, append, dt, stack_size)
    soup.append(root)
    return root if return_root else soup
