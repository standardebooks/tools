#!/usr/bin/env python3

from lxml import etree, cssselect
import regex


XHTML_NAMESPACES = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "z3998": "http://www.daisy.org/z3998/2012/vocab/structure/", "se": "https://standardebooks.org/vocab/1.0", "dc": "http://purl.org/dc/elements/1.1/", "opf": "http://www.idpf.org/2007/opf"}


class EasyXmlTree:
	_xhtml_string = ""
	etree = None

	def __init__(self, xhtml_string):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python
		self._xhtml_string = xhtml_string#.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
		self.etree = etree.fromstring(str.encode(self._xhtml_string))

	def css_select(self, selector):
		return self.xpath(cssselect.CSSSelector(selector, translator="html", namespaces=XHTML_NAMESPACES).path)

	def xpath(self, selector):
		# Warning: lxml has no support for an element without a namepace.  So, when using xpath or css_select, make sure to include a bogus namespace if necessary.
		# For example, in content.opf we can't do xpath("//metadata").  We have to use a bogus namespace: xpath("//opf:metadata")
		result = []

		for element in self.etree.xpath(selector, namespaces=XHTML_NAMESPACES):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element))

		return result



class EasyXmlElement:
	_lxml_element = None

	def __init__(self, lxml_element):
		self._lxml_element = lxml_element

	def tostring(self):
		return regex.sub(r" xmlns(:[a-z]+?)?=\"[^\"]+?\"", "", etree.tostring(self._lxml_element, encoding=str, with_tail=False))

	def inner_html(self):
		return self._lxml_element.text
