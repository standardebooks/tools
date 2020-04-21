#!/usr/bin/env python3
"""
Defines the EasyXmlTree class, which is a convenience wrapper around etree.
The class exposes some helpful functions like css_select() and xpath().
"""

from typing import Dict, List, Union
import regex
from lxml import cssselect, etree
import se


CSS_SELECTOR_CACHE: Dict[str, cssselect.CSSSelector] = {}

def css_selector(selector: str) -> cssselect.CSSSelector:
	"""
	Create a CSS selector for the given selector string. Return a cached CSS selector if
	one already exists.
	"""

	sel = CSS_SELECTOR_CACHE.get(selector)
	if not sel:
		sel = cssselect.CSSSelector(selector, translator="xhtml", namespaces=se.XHTML_NAMESPACES)
		CSS_SELECTOR_CACHE[selector] = sel
	return sel

class EasyXmlTree:
	"""
	A helper class to make some lxml operations a little less painful.
	Represents an entire lxml tree.
	"""

	def __init__(self, xml_string: str):
		self.etree = etree.fromstring(str.encode(xml_string))

	def css_select(self, selector: str) -> Union[str, list, None]:
		"""
		Shortcut to select elements based on CSS selector.
		"""

		return self.xpath(css_selector(selector).path)

	def xpath(self, selector: str, return_string: bool = False):
		"""
		Shortcut to select elements based on xpath selector.

		If return_string is true, return a single string value instead of a list.

		Warning: lxml has no support for an element without a namepace.  So, when using xpath or css_select, make sure to include a bogus namespace if necessary.
		For example, in content.opf we can't do xpath("//metadata").  We have to use a bogus namespace: xpath("//opf:metadata")
		"""

		result: List[Union[str, EasyXmlElement]] = []

		for element in self.etree.xpath(selector, namespaces=se.XHTML_NAMESPACES):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element))

		if return_string and result:
			return str(result[0])
		if return_string and not result:
			return None

		return result

class EasyXhtmlTree(EasyXmlTree):
	"""
	Wrapper for the XHTML namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", ""))

class EasySvgTree(EasyXmlTree):
	"""
	Wrapper for the SVG namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.w3.org/2000/svg\"", ""))

class EasyOpfTree(EasyXmlTree):
	"""
	Wrapper for the SVG namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.idpf.org/2007/opf\"", ""))

class EasyXmlElement:
	"""
	Represents an lxml element.
	"""

	def __init__(self, lxml_element):
		self.lxml_element = lxml_element

	def totagstring(self) -> str:
		"""
		Return a string representing the opening tag of the element.

		Example:
		`<p class="test">Hello there!</p>` -> `<p class="test">`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `<p>`
		"""

		attrs = ""

		for name, value in self.lxml_element.items():
			attrs += f" {name}=\"{value}\""

		attrs = attrs.replace("{http://www.idpf.org/2007/ops}", "epub:")
		attrs = attrs.replace("{http://www.w3.org/XML/1998/namespace}", "xml:")

		return f"<{self.lxml_element.tag}{attrs}>"

	def tostring(self) -> str:
		"""
		Return a string representing this element.

		Example:
		`<p class="test">Hello there!</p>` -> `<p class="test">Hello there!</p>`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `<p>Hello there, <abbr>Mr.</abbr> Smith!</p>`
		"""

		return regex.sub(r" xmlns(:[a-z]+?)?=\"[^\"]+?\"", "", etree.tostring(self.lxml_element, encoding=str, with_tail=False))

	def attribute(self, attribute: str) -> str:
		"""
		Return the value of an attribute on this element.
		"""


		attribute = attribute.replace("epub:", "{http://www.idpf.org/2007/ops}")

		return self.lxml_element.get(attribute)

	def xpath(self, selector: str, return_string: bool = False):
		"""
		Shortcut to select elements based on xpath selector.
		"""

		result: List[Union[str, EasyXmlElement]] = []

		for element in self.lxml_element.xpath(selector, namespaces=se.XHTML_NAMESPACES):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element))

		if return_string and result:
			return str(result[0])
		if return_string and not result:
			return None

		return result

	def inner_xml(self) -> str:
		"""
		Return a string representing the inner XML of this element.

		Note: this is not *always* the same as lxml_element.text, which only returns
		the text up to the first element node.

		Example:
		`<p class="test">Hello there!</p>` -> `Hello there!`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `Hello there, <abbr>Mr.</abbr> Smith!`
		"""

		xml = self.tostring()
		xml = regex.sub(r"^<[^>]+?>", "", xml)
		xml = regex.sub(r"<[^>]+?>$", "", xml)
		return xml

	def inner_text(self) -> str:
		"""
		Return the text portion of the inner XML, without any tags.

		Example:
		`<p class="test">Hello there!</p>` -> `Hello there!`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `Hello there, Mr. Smith!`
		"""

		return regex.sub(r"<[^>]+?>", "", self.inner_xml().strip())

	def remove(self) -> None:
		"""
		Remove this element from its dom tree.
		"""

		# lxml_element.remove() removes both the element AND following elements.
		# So, we have to have a custom remove() function here.
		# See https://forums.wikitechy.com/question/how-to-remove-an-element-in-lxml/#70204
		parent = self.lxml_element.getparent()
		if self.lxml_element.tail:
			prev = self.lxml_element.getprevious()
			if prev is not None: # We can't do `if prev` because we get a FutureWarning from lxml
				prev.tail = (prev.tail or '') + self.lxml_element.tail
			else:
				parent.text = (parent.text or '') + self.lxml_element.tail

		parent.remove(self.lxml_element)

	@property
	def text(self) -> str:
		"""
		Return only returns the text up to the first element node

		Example:
		`<p class="test">Hello there!</p>` -> `Hello there!`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `Hello there, `
		"""

		return self.lxml_element.text
