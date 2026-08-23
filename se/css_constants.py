#!/usr/bin/env python3
"""
Defines CSS constants shared across modules.
"""

# See <https://developer.mozilla.org/en-US/docs/Web/HTML/Block-level_elements>.
CSS_BLOCK_ELEMENTS = ['address', 'article', 'aside', 'blockquote', 'details', 'dialog', 'dd', 'div', 'dl', 'dt', 'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'header', 'hgroup', 'hr', 'li', 'main', 'nav', 'ol', 'p', 'pre', 'section', 'table', 'ul']
CSS_PROPERTIES = {
	'align-content': {'applies_to': 'all', 'inherited': False},
	'border': {'applies_to': 'all', 'inherited': False},
	'border-color': {'applies_to': 'all', 'inherited': False},
	'border-style': {'applies_to': 'all', 'inherited': False},
	'border-width': {'applies_to': 'all', 'inherited': False},
	'color': {'applies_to': 'all', 'inherited': True},
	'display': {'applies_to': 'all', 'inherited': False},
	'font-style': {'applies_to': 'all', 'inherited': True},
	'font-variant': {'applies_to': 'all', 'inherited': True},
	'font-variant-numeric': {'applies_to': 'all', 'inherited': True},
	'height': {'applies_to': 'all', 'inherited': False},
	'margin': {'applies_to': 'all', 'inherited': False},
	'margin-top': {'applies_to': 'all', 'inherited': False},
	'margin-right': {'applies_to': 'all', 'inherited': False},
	'margin-bottom': {'applies_to': 'all', 'inherited': False},
	'margin-left': {'applies_to': 'all', 'inherited': False},
	'max-height': {'applies_to': 'all', 'inherited': False},
	'max-width': {'applies_to': 'all', 'inherited': False},
	'padding': {'applies_to': 'all', 'inherited': False},
	'padding-top': {'applies_to': 'all', 'inherited': False},
	'padding-bottom': {'applies_to': 'all', 'inherited': False},
	'padding-right': {'applies_to': 'all', 'inherited': False},
	'padding-left': {'applies_to': 'all', 'inherited': False},
	'text-align': {'applies_to': 'block', 'inherited': True},
	'text-indent': {'applies_to': 'block', 'inherited': True},
	'width': {'applies_to': 'all', 'inherited': False},
}
