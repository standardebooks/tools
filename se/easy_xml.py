#!/usr/bin/env python3
"""
Defines the EasyXmlTree class, which is a convenience wrapper around etree.
The class exposes some helpful functions like css_select() and xpath().
"""

from html import unescape
from typing import Dict, List, Union, Optional
import unicodedata

import regex
from lxml import cssselect, etree
from cssselect import parser

# Not sure how to get around pylint error, so just ignore it for now
# until someone can solve it
import se # pylint: disable=cyclic-import
import se.css # pylint: disable=cyclic-import

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

	This is not a complete XML parser. It only works if namespaces are only declared on the root element.
	"""

	def __init__(self, xml: Union[str, etree._ElementTree]):
		self.namespaces = {"re": "http://exslt.org/regular-expressions", "xml": "http://www.w3.org/XML/1998/namespace"} # Enable regular expressions in xpath; xml is the default xml namespace
		self.default_namespace = None

		if isinstance(xml, etree._ElementTree):
			xml_string = etree.tostring(xml, encoding="unicode", with_tail=False)
		else:
			xml_string = xml

		# Save the default namespace for later
		for namespace in regex.findall(r" xmlns=\"([^\"]+?)\"", xml_string):
			self.default_namespace = namespace

		# Always remove the default namespaces, otherwise xpath with lxml is a huge pain
		xml_string = regex.sub(r" xmlns=\"[^\"]+?\"", "", xml_string)

		# Add additional namespaces we may have
		for match in regex.findall(r" xmlns:(.+?)=\"([^\"]+?)\"", xml_string):
			self.namespaces[match[0]] = match[1]

		try:
			# huge_tree allows XML files of arbitrary size, like Ulysses S. Grant
			custom_parser = etree.XMLParser(huge_tree=True)
			self.etree = etree.fromstring(str.encode(xml_string), parser=custom_parser)
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
				sel = cssselect.CSSSelector(selector, translator="xhtml", namespaces=self.namespaces)
				CSS_SELECTOR_CACHE[selector] = sel

			return self.xpath(sel.path)
		except parser.SelectorSyntaxError as ex:
			raise se.InvalidCssException(f"Invalid selector: [css]{selector}[/]") from ex

	def xpath(self, selector: str, return_string: bool = False):
		"""
		Shortcut to select elements based on xpath selector.

		If return_string is true, return a single string value instead of a list.
		"""

		result: List[Union[str, EasyXmlElement, float]] = []

		try:
			query_result = self.etree.xpath(selector, namespaces=self.namespaces)
			if isinstance(query_result, etree._ElementUnicodeResult): # pylint: disable=protected-access
				result.append(str(query_result))
			elif isinstance(query_result, float):
				result.append(query_result)
			else:
				for element in query_result:
					if isinstance(element, etree._ElementUnicodeResult): # pylint: disable=protected-access
						result.append(str(element))
					elif isinstance(element, str):
						result.append(element)
					else:
						result.append(EasyXmlElement(element, self.namespaces))

		except etree.XPathEvalError as ex:
			# If we ask for an undefined namespace prefix, just return nothing
			# instead of crashing
			if str(ex) != "Undefined namespace prefix":
				raise ex

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

	def apply_css(self, css: str, filename: Optional[str] = None):
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

		xml = etree.tostring(self.etree, encoding="unicode")

		# Re-insert the default namespace if we removed it earlier
		if self.default_namespace:
			xml = regex.sub(r"^<([a-z0-9\-]+)\b", fr'<\1 xmlns="{self.default_namespace}"', xml)

		xml = """<?xml version="1.0" encoding="utf-8"?>\n""" + xml + "\n"

		# Normalize unicode characters
		xml = unicodedata.normalize("NFC", xml)

		return xml

class EasyXmlElement:
	"""
	Represents an lxml element.
	"""

	def __init__(self, lxml_element: Union[str, etree._ElementTree], namespaces=None):
		self.namespaces = namespaces

		if isinstance(lxml_element, str):
			dom = EasyXmlTree(lxml_element)
			self.lxml_element = dom.etree
		else:
			self.lxml_element = lxml_element

	def _replace_shorthand_namespaces(self, value:str) -> str:
		"""
		Given a string starting with a shorthand namespace, return
		the fully qualified namespace.

		This is useful for passing to raw lxml operations as lxml doesn't understand
		shorthand namespaces.

		Example:
		epub:type -> {http://www.idpf.org/2007/ops}:type
		"""

		output = value

		if self.namespaces:
			for name, identifier in self.namespaces.items():
				output = regex.sub(fr"^{name}:", f"{{{identifier}}}", output)

		return output

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
				# Replace long namespaces from lxml with shorthand
				short_name = name
				for namespace, identifier in self.namespaces.items():
					short_name = short_name.replace(f"{{{identifier}}}", f"{namespace}:")

				attrs += f" {short_name}=\"{value}\""

		tag_name = self.lxml_element.tag
		for namespace, identifier in self.namespaces.items():
			tag_name = tag_name.replace(f"{{{identifier}}}", f"{namespace}:")

		return f"<{tag_name}{attrs}>"

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

	def remove_attr(self, attribute: str) -> None:
		"""
		Remove an attribute from this node.
		"""

		try:
			self.lxml_element.attrib.pop(self._replace_shorthand_namespaces(attribute))
		except KeyError:
			# If the attribute doesn't exist, just continue
			pass

	def add_attr_value(self, attribute: str, value: str) -> None:
		"""
		Add a space-separated attribute value to the target attribute.
		If the attribute doesn't exist, add it.

		Mainly useful for HTML `class` attributes and epub `epub:type` attributes.

		Example adding value `bar` to the `class` attribute:
		<p class="foo"> -> <p class="foo bar">
		"""

		existing_value = self.get_attr(attribute) or ""

		self.set_attr(attribute, (existing_value + " " + value).strip())

	def remove_attr_value(self, attribute: str, value: str) -> None:
		"""
		Remove a space-separated attribute value from the target attribute.
		If removing the value makes the attribute empty, remove the attribute.

		Mainly useful for HTML `class` attributes and epub `epub:type` attributes.

		Example removing value `bar` from the `class` attribute:
		<p class="foo bar"> -> <p class="foo">
		"""

		if self.get_attr(attribute):
			self.set_attr(attribute, regex.sub(fr"\s*\b{regex.escape(value)}\b\s*", "", self.get_attr(attribute)))

			# If the attribute is now empty, remove it
			if not self.get_attr(attribute):
				self.remove_attr(attribute)

	def get_attr(self, attribute: str) -> str:
		"""
		Return the value of an attribute on this element.
		"""

		return self.lxml_element.get(self._replace_shorthand_namespaces(attribute))

	def set_attr(self, attribute: str, value: str) -> str:
		"""
		Set the value of an attribute on this element.
		"""

		return self.lxml_element.set(self._replace_shorthand_namespaces(attribute), value)

	def xpath(self, selector: str, return_string: bool = False):
		"""
		Shortcut to select elements based on xpath selector.
		"""

		result: List[Union[str, EasyXmlElement, float]] = []

		query_result = self.lxml_element.xpath(selector, namespaces=self.namespaces)
		if isinstance(query_result, etree._ElementUnicodeResult): # pylint: disable=protected-access
			result.append(str(query_result))
		elif isinstance(query_result, float):
			result.append(query_result)
		else:
			for element in query_result:
				if isinstance(element, etree._ElementUnicodeResult): # pylint: disable=protected-access
					result.append(str(element))
				elif isinstance(element, str):
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

		return unescape(regex.sub(r"<[^>]+?>", "", self.inner_xml().strip()))

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
				prev.tail = (prev.tail or "") + self.lxml_element.tail
			else:
				parent.text = (parent.text or "") + self.lxml_element.tail

		parent.remove(self.lxml_element)

	def wrap_with(self, node) -> None:
		"""
		Wrap this node in the passed node.
		"""

		self.lxml_element.addprevious(node.lxml_element)
		node.lxml_element.insert(0, self.lxml_element)

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
				if parent is not None:
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

	def replace_outer(self, node) -> None:
		"""
		Replace this node's wrapping element with the wrapping element of the passed
		node, but keep this node's children.

		Example:
		<p>foo <b>bar</b></p> -> <div class="baz">foo <b>bar</b></div>
		"""

		node.lxml_element.tail = self.lxml_element.tail
		node.lxml_element.text = self.lxml_element.text
		node.children = self.children

		self.lxml_element.text = ""
		self.lxml_element.tail = ""
		self.lxml_element.addnext(node.lxml_element)
		self.unwrap()

	def replace_with(self, node) -> None:
		"""
		Remove this node and replace it with the passed node
		"""

		# lxml.addnext() moves this element's tail to the new element
		if isinstance(node, EasyXmlElement):
			self.lxml_element.addnext(node.lxml_element)
		else:
			self.lxml_element.addnext(node)

		self.remove()

	def append(self, node) -> None:
		"""
		Place node as the last child of this node.
		"""

		if isinstance(node, EasyXmlElement):
			self.lxml_element.append(node.lxml_element)
		else:
			self.lxml_element.append(node)

	def prepend(self, node) -> None:
		"""
		Place node as the first child of this node.
		"""

		# If the node we're inserting in to has text, lxml will insert the new
		# node *after* the text. So, we have to make the node's lxml `.text`
		# the new node's lxml `.tail`.
		target = node
		if isinstance(node, EasyXmlElement):
			target = node.lxml_element

		if self.lxml_element.text:
			if target.tail:
				target.tail = target.tail + self.lxml_element.text
			else:
				target.tail = self.lxml_element.text

		self.lxml_element.insert(0, target)
		self.lxml_element.text = ""

	def set_text(self, string: str) -> None:
		"""
		Replace all contents of this node, including text and any child nodes, with a text string.
		"""

		for child in list(self.lxml_element):
			self.lxml_element.remove(child)

		self.lxml_element.text = string

	@property
	def children(self) -> List:
		"""
		Return a list representing of this node's direct children
		"""
		children = []

		for child in self.lxml_element:
			children.append(EasyXmlElement(child, self.namespaces))

		return children

	@children.setter
	def children(self, children) -> None:
		"""
		Set the node's children.
		"""

		for child in self.lxml_element:
			self.lxml_element.remove(child)

		for child in children:
			if isinstance(child, EasyXmlElement):
				self.lxml_element.append(child.lxml_element)
			else:
				self.lxml_element.append(child)

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

	@text.setter
	def text(self, value: str) -> None:
		"""
		Set the lxml text attribute (the text up to the first child element)
		"""

		self.lxml_element.text = value

	@property
	def tail(self) -> str:
		"""
		Return only returns the text after this node

		Example:
		`<p class="test">Hello there!</p>` -> ``
		`<p class="test">Hello there!</p> he said.` -> ` he said.`
		"""

		return self.lxml_element.tail

	@tail.setter
	def tail(self, value: str) -> None:
		"""
		Set the lxml tail attribute (the text after this element)
		"""

		self.lxml_element.tail = value

	@property
	def attrs(self) -> Dict:
		"""
		Return a dict of attributes for this node
		"""

		return self.lxml_element.attrib

	@attrs.setter
	def attrs(self, value: Dict) -> None:
		"""
		Return a dict of attributes for this node
		"""

		self.lxml_element.attrib.clear()

		for name, val in sorted(value.items()):
			self.set_attr(name, val)
