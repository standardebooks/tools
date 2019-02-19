#!/usr/bin/env python3
"""
Defines the EasyXmlTree class, which is a convenience wrapper around etree.
The class exposes some helpful functions like css_select() and xpath().
"""

import regex
from lxml import etree, cssselect
import se


class EasyXmlTree:
	"""
	A helper class to make some lxml operations a little less painful.
	Represents an entire lxml tree.
	"""

	_xhtml_string = ""
	etree = None

	def __init__(self, xhtml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all.  See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		self._xhtml_string = xhtml_string#.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", "")
		self.etree = etree.fromstring(str.encode(self._xhtml_string))

	def css_select(self, selector: str) -> list:
		"""
		Shortcut to select elements based on CSS selector.
		"""

		return self.xpath(cssselect.CSSSelector(selector, translator="html", namespaces=se.XHTML_NAMESPACES).path)

	def xpath(self, selector: str) -> list:
		"""
		Shortcut to select elements based on xpath selector.

		Warning: lxml has no support for an element without a namepace.  So, when using xpath or css_select, make sure to include a bogus namespace if necessary.
		For example, in content.opf we can't do xpath("//metadata").  We have to use a bogus namespace: xpath("//opf:metadata")
		"""

		result = []

		for element in self.etree.xpath(selector, namespaces=se.XHTML_NAMESPACES):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element))

		return result



class EasyXmlElement:
	"""
	Represents an lxml element.
	"""
	__lxml_element = None

	def __init__(self, lxml_element):
		self.__lxml_element = lxml_element

	def tostring(self) -> str:
		"""
		Return a string representing this element.
		"""

		return regex.sub(r" xmlns(:[a-z]+?)?=\"[^\"]+?\"", "", etree.tostring(self.__lxml_element, encoding=str, with_tail=False))

	def attribute(self, attribute: str) -> str:
		"""
		Return the value of an attribute on this element.
		"""
		return self.__lxml_element.get(attribute)

	def inner_html(self) -> str:
		"""
		Return a string representing the inner HTML of this element.
		"""

		return self.__lxml_element.text
