#!/usr/bin/env python3
"""
Defines the EasyXmlTree class, which is a convenience wrapper around etree.
The class exposes some helpful functions like css_select() and xpath().
"""

from typing import Dict, List, Union
import unicodedata

import regex
from lxml import cssselect, etree
from cssselect import parser

import se
import se.css

CSS_SELECTOR_CACHE: Dict[str, cssselect.CSSSelector] = {}
CSS_RULES_CACHE: Dict[str, List[se.css.CssRule]] = {}

def escape_xpath(string: str) -> str:
	"""
	Xpath string literals don't have escape sequences for ' and "
	So to escape them, we have to use the xpath concat() function.
	See https://stackoverflow.com/a/6938681

	This function returns the *enclosing quotes*, so it must be used without them. For example:
	dom.xpath(f"//title[text() = {se.easy_xml.escape_xpath(title)}]")
	"""

	if "'" not in string:
		return f"'{string}'"

	if '"' not in string:
		return f'"{string}"'

	# Can't use f-strings here because f-strings can't contain \ escapes
	return "concat('%s')" % string.replace("'", "',\"'\",'")

class EasyXmlTree:
	"""
	A helper class to make some lxml operations a little less painful.
	Represents an entire lxml tree.
	"""

	def __init__(self, xml_string: str):
		self.namespaces = {"re": "http://exslt.org/regular-expressions"} # Enable regular expressions in xpath
		try:
			self.etree = etree.fromstring(str.encode(xml_string))
		except etree.XMLSyntaxError as ex:
			raise se.InvalidXmlException(f"Couldn’t parse XML. Exception: {ex}") from ex

		self.is_css_applied = False

	def css_select(self, selector: str):
		"""
		Shortcut to select elements based on CSS selector.
		"""

		try:
			sel = CSS_SELECTOR_CACHE.get(selector)
			if not sel:
				sel = cssselect.CSSSelector(selector, translator="xhtml", namespaces={"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops"})
				CSS_SELECTOR_CACHE[selector] = sel

			return self.xpath(sel.path)
		except parser.SelectorSyntaxError as ex:
			raise se.InvalidCssException(f"Invalid selector: [css]{selector}[/]") from ex

	def xpath(self, selector: str, return_string: bool = False):
		"""
		Shortcut to select elements based on xpath selector.

		If return_string is true, return a single string value instead of a list.

		Warning: lxml has no support for an element without a namepace.  So, when using xpath or css_select, make sure to include a bogus namespace if necessary.
		For example, in content.opf we can't do xpath("//metadata").  We have to use a bogus namespace: xpath("//opf:metadata")
		"""

		result: List[Union[str, EasyXmlElement]] = []

		for element in self.etree.xpath(selector, namespaces=self.namespaces):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element, self.namespaces))

		if return_string and result:
			return str(result[0])
		if return_string and not result:
			return None

		return result

	@staticmethod
	def _apply_css_declaration_to_node(node, declaration: se.css.CssDeclaration, specificity_number: int):
		if declaration.applies_to == "all" or (declaration.applies_to == "block" and node.tag in se.css.CSS_BLOCK_ELEMENTS):
			existing_specificity = node.get_attr(f"data-css-{declaration.name}-specificity") or 0

			if declaration.important:
				specificity_number = specificity_number + 1000

			if int(existing_specificity) <= specificity_number:
				node.set_attr(f"data-css-{declaration.name}", declaration.value)
				node.set_attr(f"data-css-{declaration.name}-specificity", str(specificity_number))

	def apply_css(self, css: str, filename: str=None):
		"""
		Apply a CSS stylesheet to an XHTML tree.
		The application is naive and should not be expected to be browser-grade.
		CSS properties on specific elements can be returned using EasyXmlElement.get_css_property()

		With filename, save the resulting rules in a cache to prevent having to re-parse
		the same stylesheet over and over.

		Currently this does not support rules/declarations in @ blocks like @supports.

		For example,

		for node in dom.xpath("//em")"
			print(node.get_css_property("font-style"))
		"""
		self.is_css_applied = True

		if filename and filename in CSS_RULES_CACHE:
			rules = CSS_RULES_CACHE[filename]
		else:
			rules = se.css.parse_rules(css)
			if filename:
				CSS_RULES_CACHE[filename] = rules

		# We've parsed the CSS, now apply it to the DOM tree
		for rule in rules:
			try:
				for node in self.css_select(rule.selector):
					for declaration in rule.declarations:
						self._apply_css_declaration_to_node(node, declaration, rule.specificity_number)

						# If the property is inherited, apply it to its descendants
						# However inherited properties get 0 specificity, because they can be overriden
						if declaration.inherited:
							for child in node.xpath(".//*"):
								self._apply_css_declaration_to_node(child, declaration, 0)

			except cssselect.ExpressionError:
				# This gets thrown on some selectors not yet implemented by lxml, like *:first-of-type
				pass

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		# If we applied a CSS file to this tree, remove the special attributes we
		# added before printing it out.
		if self.is_css_applied:
			for node in self.xpath("//@*[starts-with(name(), 'data-css-')]/parent::*"):
				for attr in node.lxml_element.attrib:
					if attr.startswith("data-css-"):
						node.remove_attr(attr)

		xml = """<?xml version="1.0" encoding="utf-8"?>\n""" + etree.tostring(self.etree, encoding="unicode") + "\n"

		# Normalize unicode characters
		xml = unicodedata.normalize("NFC", xml)

		return xml

class EasyContainerTree(EasyXmlTree):
	"""
	Wrapper for the container namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		super().__init__(xml_string.replace(" xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\"", ""))

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = EasyXmlTree.to_string(self)

		xml = regex.sub(r"<container(?!:)", "<container xmlns=\"urn:oasis:names:tc:opendocument:xmlns:container\"", xml)

		return xml

class EasyXhtmlTree(EasyXmlTree):
	"""
	Wrapper for the XHTML namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		super().__init__(xml_string.replace(" xmlns=\"http://www.w3.org/1999/xhtml\"", ""))

		self.namespaces = {**self.namespaces, **{"epub": "http://www.idpf.org/2007/ops", "m": "http://www.w3.org/1998/Math/MathML"}}

	def to_string(self) -> str:
		"""
		Serialize the tree to a string.
		"""

		xml = EasyXmlTree.to_string(self)

		xml = regex.sub(r"<html(?!:)", "<html xmlns=\"http://www.w3.org/1999/xhtml\"", xml)

		return xml

class EasySvgTree(EasyXmlTree):
	"""
	Wrapper for the SVG namespace.
	"""

	def __init__(self, xml_string: str):
		# We have to remove the default namespace declaration from our document, otherwise
		# xpath won't find anything at all. See http://stackoverflow.com/questions/297239/why-doesnt-xpath-work-when-processing-an-xhtml-document-with-lxml-in-python

		super().__init__(xml_string.replace(" xmlns=\"http://www.w3.org/2000/svg\"", ""))

		self.namespaces = {**self.namespaces, **{"xlink": "http://www.w3.org/1999/xlink"}}

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

		super().__init__(xml_string.replace(" xmlns=\"http://www.idpf.org/2007/opf\"", ""))

		self.namespaces = {**self.namespaces, **{"dc": "http://purl.org/dc/elements/1.1/"}}

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

	def __init__(self, lxml_element, namespaces=None):
		self.namespaces = namespaces
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
			# Exclude applied CSS
			if not name.startswith("data-css-"):
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

		value = etree.tostring(self.lxml_element, encoding=str, with_tail=False)

		# Remove namespaces
		value = regex.sub(r" xmlns(:[\p{Letter}]+?)?=\"[^\"]+?\"", "", value)

		# Remove applied CSS
		value = regex.sub(r" data-css-[a-z\-]+?=\"[^\"]*?\"", "", value)

		return value

	def get_css(self) -> Dict:
		"""
		Return a dict of CSS properties applied to this node.
		"""

		output = {}
		for attr, value in self.lxml_element.attrib.items():
			if attr.startswith("data-css-"):
				output[attr.replace("data-css-", "")] = value

		return output

	def get_css_property(self, property_name: str):
		"""
		Return the applied CSS value for the given property name, like `border-color`,
		or None if it does not exist.
		"""

		if f"data-css-{property_name}" in self.lxml_element.attrib:
			return self.lxml_element.attrib[f"data-css-{property_name}"]

		return None

	def remove_attr(self, attribute: str):
		"""
		Remove an attribute from this node.
		"""

		etree.strip_attributes(self.lxml_element, attribute)

	def get_attr(self, attribute: str) -> str:
		"""
		Return the value of an attribute on this element.
		"""

		attribute = attribute.replace("epub:", "{http://www.idpf.org/2007/ops}")
		attribute = attribute.replace("xml:", "{http://www.w3.org/XML/1998/namespace}")

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

		for element in self.lxml_element.xpath(selector, namespaces=self.namespaces):
			if isinstance(element, str):
				result.append(element)
			else:
				result.append(EasyXmlElement(element, self.namespaces))

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

		return EasyXmlElement(self.lxml_element.getparent(), self.namespaces)

	@property
	def text(self) -> str:
		"""
		Return only returns the text up to the first element node

		Example:
		`<p class="test">Hello there!</p>` -> `Hello there!`
		`<p>Hello there, <abbr>Mr.</abbr> Smith!</p>` -> `Hello there, `
		"""

		return self.lxml_element.text
