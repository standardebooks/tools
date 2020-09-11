#!/usr/bin/env python3
"""
Defines the EasyXmlTree class, which is a convenience wrapper around etree.
The class exposes some helpful functions like css_select() and xpath().
"""

from typing import Dict, List, Union
import unicodedata

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

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = """<?xml version="1.0" encoding="utf-8"?>\n""" + etree.tostring(self.etree, encoding="unicode") + "\n"

		# Normalize unicode characters
		xml = unicodedata.normalize("NFC", xml)

		return xml

class EasyXhtmlTree(EasyXmlTree):
	"""
	Wrapper for the XHTML namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", ""))

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = EasyXmlTree.to_string(self)

		xml = xml.replace("<html", "<html xmlns=\"http://www.w3.org/1999/xhtml\"")

		return xml

class EasySvgTree(EasyXmlTree):
	"""
	Wrapper for the SVG namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.w3.org/2000/svg\"", ""))

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = EasyXmlTree.to_string(self)

		xml = xml.replace("<svg", "<svg xmlns=\"http://www.w3.org/2000/svg\"")

		return xml

class EasyOpfTree(EasyXmlTree):
	"""
	Wrapper for the OPF namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		EasyXmlTree.__init__(self, xml_string.replace(" xmlns=\"http://www.idpf.org/2007/opf\"", ""))

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = EasyXmlTree.to_string(self)

		xml = xml.replace("<package", "<package xmlns=\"http://www.idpf.org/2007/opf\"")

		return xml

class EasyXmlElement:
	"""
	Represents an lxml element.
	"""

	def __init__(self, lxml_element):
		self.lxml_element = lxml_element

	def to_tag_string(self) -> str:
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

	def to_string(self) -> str:
		"""
		Return a string representing this element.

		Example:
		`<p class="test">Hello there!</p>` -> `<p class="test">Hello there!</p>`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `<p>Hello there, <abbr>Mr.</abbr> Smith!</p>`
		"""

		return regex.sub(r" xmlns(:[\p{Letter}]+?)?=\"[^\"]+?\"", "", etree.tostring(self.lxml_element, encoding=str, with_tail=False))

	def get_attr(self, attribute: str) -> str:
		"""
		Return the value of an attribute on this element.
		"""

		attribute = attribute.replace("epub:", "{http://www.idpf.org/2007/ops}")

		return self.lxml_element.get(attribute)

	def set_attr(self, attribute: str, value: str) -> str:
		"""
		Set the value of an attribute on this element.
		"""

		attribute = attribute.replace("epub:", "{http://www.idpf.org/2007/ops}")

		return self.lxml_element.set(attribute, value)

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

		xml = self.to_string()
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

	def unwrap(self) -> None:
		"""
		Remove the element's wrapping tag and replace it with the element's contents.
		"""

		# In lxml, there are no "text nodes" like in a classic DOM. There are only element nodes.
		# An element has a `.text` property which is the child text UP TO THE FIRST CHILD ELEMENT.
		# An element's `.tail` property contains text *after* the element, up to its first element sibling.

		parent = self.lxml_element.getparent()

		children = self.lxml_element.getchildren()

		children.reverse()

		# This will *move* each child element node to *after* the current element.
		# Since any following text is stored in the child element's .tail, this will *also*
		# move that text.
		for child in children:
			self.lxml_element.addnext(child)

		# Now we've moved all child elements and the text following them. But what if there's
		# text *before* any child elements? That is stored in the .text property.
		if self.lxml_element.text:
			prev = self.lxml_element.getprevious()
			if prev is None:
				if parent.text:
					parent.text = parent.text + self.lxml_element.text
				else:
					parent.text = self.lxml_element.text
			else:
				if prev.tail:
					prev.tail = prev.tail + self.lxml_element.text
				else:
					prev.tail = self.lxml_element.text

		# This calls the EasyXmlTree.remove() function, not an lxml function
		self.remove()

	def replace_with(self, node) -> None:
		"""
		Remove this node and replace it with the passed node
		"""

		self.lxml_element.addnext(node.lxml_element)
		self.remove()

	def append(self, node) -> None:
		"""
		Place node as the last child of this node.
		"""

		if isinstance(node, EasyXmlElement):
			self.lxml_element.append(node.lxml_element)

		else:
			self.lxml_element.append(node)

	@property
	def tag(self) -> str:
		"""
		Return a string representing this node's tag name, like `body` or `section`
		"""

		return self.lxml_element.tag

	@property
	def parent(self): # This returns an EasyXmlElement but we can't type hint this until Python 3.10
		"""
		Return an EasyXmlElement representing this node's parent node
		"""

		return EasyXmlElement(self.lxml_element.getparent())

	@property
	def text(self) -> str:
		"""
		Return only returns the text up to the first element node

		Example:
		`<p class="test">Hello there!</p>` -> `Hello there!`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `Hello there, `
		"""

		return self.lxml_element.text
