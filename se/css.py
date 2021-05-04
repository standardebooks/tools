#!/usr/bin/env python3
"""
Defines various CSS classes and helper functions.
"""

from copy import deepcopy

from typing import List

import regex
import tinycss2
import tinycss2.color3

import se

# See https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements
CSS_BLOCK_ELEMENTS = ["address", "article", "aside", "blockquote", "details", "dialog", "dd", "div", "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "ul"]
CSS_PROPERTIES = {
			"align-content": {"applies_to": "all", "inherited": False},
			"border": {"applies_to": "all", "inherited": False},
			"border-color": {"applies_to": "all", "inherited": False},
			"border-style": {"applies_to": "all", "inherited": False},
			"border-width": {"applies_to": "all", "inherited": False},
			"color": {"applies_to": "all", "inherited": True},
			"display": {"applies_to": "all", "inherited": False},
			"font-style": {"applies_to": "all", "inherited": True},
			"font-variant": {"applies_to": "all", "inherited": True},
			"font-variant-numeric": {"applies_to": "all", "inherited": True},
			"height": {"applies_to": "all", "inherited": False},
			"margin": {"applies_to": "all", "inherited": False},
			"margin-top": {"applies_to": "all", "inherited": False},
			"margin-right": {"applies_to": "all", "inherited": False},
			"margin-bottom": {"applies_to": "all", "inherited": False},
			"margin-left": {"applies_to": "all", "inherited": False},
			"max-height": {"applies_to": "all", "inherited": False},
			"max-width": {"applies_to": "all", "inherited": False},
			"padding": {"applies_to": "all", "inherited": False},
			"padding-top": {"applies_to": "all", "inherited": False},
			"padding-bottom": {"applies_to": "all", "inherited": False},
			"padding-right": {"applies_to": "all", "inherited": False},
			"padding-left": {"applies_to": "all", "inherited": False},
			"text-align": {"applies_to": "block", "inherited": True},
			"text-indent": {"applies_to": "block", "inherited": True},
			"width": {"applies_to": "all", "inherited": False},
		}

class CssDeclaration:
	"""
	A CSS declaration, i.e., <declaration>: <value>;
	"""

	def __init__(self, name: str, values, important: bool):
		self.name = name
		self.value = tinycss2.serialize(values).strip()
		self.important = important
		self.raw_values = values

		if self.name in CSS_PROPERTIES:
			self.applies_to = CSS_PROPERTIES[self.name]["applies_to"]
			self.inherited = CSS_PROPERTIES[self.name]["inherited"]
		else:
			self.applies_to = "all"
			self.inherited = True

	def expand(self):
		"""
		Given a declaration, if it is shorthand like `margin` (short for `margin-left`, `margin-top`, etc.)
		then break it apart into its complete component declarations
		"""

		output = []

		if self.name in ("margin", "padding", "border-color", "border-style", "border-width"):
			matches = regex.split(r"\s", self.value)

			identifiers = regex.split(r"-", self.name)

			base_name = identifiers[0] # i.e. `border`
			style_name = "" # i.e. `style`
			if len(identifiers) == 2:
				style_name = f"-{identifiers[1]}"

			if len(matches) == 1:
				for side in ["-top", "-right", "-bottom", "-left"]:
					expanded_declaration = deepcopy(self)
					expanded_declaration.name = base_name + side + style_name
					output.append(expanded_declaration)

			if len(matches) == 2:
				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-top" + style_name
				expanded_declaration.value = matches[0]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-right" + style_name
				expanded_declaration.value = matches[1]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-bottom" + style_name
				expanded_declaration.value = matches[0]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-left" + style_name
				expanded_declaration.value = matches[1]
				output.append(expanded_declaration)

			if len(matches) == 3:
				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-top" + style_name
				expanded_declaration.value = matches[0]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-right" + style_name
				expanded_declaration.value = matches[1]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-bottom" + style_name
				expanded_declaration.value = matches[2]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-left" + style_name
				expanded_declaration.value = matches[1]
				output.append(expanded_declaration)

			if len(matches) == 4:
				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-top" + style_name
				expanded_declaration.value = matches[0]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-right" + style_name
				expanded_declaration.value = matches[1]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-bottom" + style_name
				expanded_declaration.value = matches[2]
				output.append(expanded_declaration)

				expanded_declaration = deepcopy(self)
				expanded_declaration.name = base_name + "-left" + style_name
				expanded_declaration.value = matches[3]
				output.append(expanded_declaration)

		elif self.name == "border":
			# border is short for <border-width>, <border-style>, and <border-color>, in any order.
			# Make an attempt to parse it here.

			border_color = None
			border_width = None
			border_style = None

			for item in self.raw_values:
				if not border_color:
					# This returns None if the value is an invalid color or an RGBA tuple otherwise
					border_color = tinycss2.color3.parse_color(item)

					if border_color:
						border_color = f"rgba({border_color[0]},{border_color[1]},{border_color[2]},{border_color[3]})"

				if item.type == "ident":
					border_style = item.value
				elif item.type == "dimension":
					if item.int_value:
						border_width = str(item.int_value) + item.lower_unit
					else:
						border_width = str(item.value) + item.lower_unit

			if border_color:
				for expanded_name in ["-top", "-right", "-bottom", "-left"]:
					expanded_declaration = deepcopy(self)
					expanded_declaration.name = "border" + expanded_name + "-color"
					expanded_declaration.value = border_color
					output.append(expanded_declaration)

			if border_width:
				for expanded_name in ["-top", "-right", "-bottom", "-left"]:
					expanded_declaration = deepcopy(self)
					expanded_declaration.name = "border" + expanded_name + "-width"
					expanded_declaration.value = border_width
					output.append(expanded_declaration)

			if border_style:
				for expanded_name in ["-top", "-right", "-bottom", "-left"]:
					expanded_declaration = deepcopy(self)
					expanded_declaration.name = "border" + expanded_name + "-style"
					expanded_declaration.value = border_style
					output.append(expanded_declaration)

		else:
			output.append(self)

		return output

class CssRule():
	"""
	A CSS stanza, including a selector and all declarations within the selector's {} block.
	"""

	def __init__(self, selector: str):
		self.selector = selector
		self.specificity = (0, 0, 0)
		self.specificity_number = 0
		self.declarations: List[CssDeclaration] = []

def parse_rules(css: str):
	"""
	Apply a CSS stylesheet to an XHTML tree.
	The application is naive and should not be expected to be browser-grade.
	CSS declarationerties on specific elements can be returned using EasyXmlElement.get_css_declarationerty()

	For example,

	for node in dom.xpath("//em")"
		print(node.get_css_declarationerty("font-style"))
	"""

	rules = []

	# Parse the stylesheet to break it into rules and their associated declarationerties
	for token in tinycss2.parse_stylesheet(css, skip_comments=True):
		if token.type == "error":
			raise se.InvalidCssException(token.message)

		# A CSS rule
		if token.type == "qualified-rule":
			selectors = tinycss2.serialize(token.prelude).strip()

			# First, get a list of declarations within the { } block.
			# Parse each declaration and add it to the rule
			declarations = []
			for item in tinycss2.parse_declaration_list(token.content):
				if item.type == "error":
					raise se.InvalidCssException("Couldn’t parse CSS. Exception: {token.message}")

				if item.type == "declaration":
					declaration = CssDeclaration(item.lower_name, item.value, item.important)
					declarations += declaration.expand()

			# We can have multiple selectors in a rule separated by `,`
			for selector in selectors.split(","):
				# Skip selectors containing pseudo elements
				if "::" in selector:
					continue

				selector = selector.strip()

				rule = CssRule(selector)

				# Calculate the specificity of the selector
				# See https://www.w3.org/TR/CSS2/cascade.html#specificity
				# a = 0 always (no style attributes apply here)

				# First remove strings, because they can contain `:`
				selector = regex.sub(r"\"[^\"]+?\"", "", selector)

				# b = number of ID attributes
				specificity_b = len(regex.findall(r"#", selector))

				# c = number of other attributes or pseudo classes
				specificity_c = len(regex.findall(r"[\.\[\:]", selector))

				# d = number of element names and pseudo elements (which will be 0 for us)
				specificity_d = len(regex.findall(r"(?:^[a-z]|\s[a-z])", selector))

				rule.specificity = (specificity_b, specificity_c, specificity_d)

				rule.specificity_number = specificity_b * 100 + specificity_c * 10 + specificity_d

				# Done with specificity, assign the declarations and save the rule

				rule.declarations = declarations

				rules.append(rule)

	return rules
