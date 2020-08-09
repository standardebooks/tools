#!/usr/bin/env python3
"""
Defines functions used by the build script to build Kobo kepub.

Kobo functions based on code from the Calibre Kobo Touch Extended Driver

https://www.mobileread.com/forums/showthread.php?t=211135
"""

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
# Copyright (C) 2013, Joel Goguen <jgoguen@jgoguen.ca>

from copy import deepcopy
import regex
import lxml.etree as etree

import se

# Don't capitalize these, they're not constants
paragraph_counter = 1
segment_counter = 1

def append_kobo_spans_from_text(node, text):
	global paragraph_counter
	global segment_counter

	if text is not None:
		# If text is only whitespace, don't add spans
		if regex.match(r"^\s+$", text, flags=regex.MULTILINE):
			return False
		else:
			# Split text in sentences
			groups = regex.split(fr'(.*?[\.\!\?\:](?:{se.HAIR_SPACE}…)?[\'"\u201d\u2019]?(?:{se.HAIR_SPACE}\u201d)?\s*)', text, flags=regex.MULTILINE)
			# Remove empty strings resulting from split()
			groups = [g for g in groups if g != ""]

			# To match Kobo KePubs, the trailing whitespace needs to be
			# prepended to the next group. Probably equivalent to make sure
			# the space stays in the span at the end.
			# add each sentence in its own span
			for group in groups:
				span = etree.Element("{%s}span" % ("http://www.w3.org/1999/xhtml", ), attrib={"id": "kobo.{0}.{1}".format(paragraph_counter, segment_counter), "class": "koboSpan"})
				span.text = group
				node.append(span)
				segment_counter += 1
			return True
	return True

def add_kobo_spans_to_node(node):
	global paragraph_counter
	global segment_counter

	# Process node only if it is not a comment or a processing instruction
	if not (node is None or isinstance(node, etree._Comment) or isinstance(node, etree._ProcessingInstruction)):
		# Special case: <img> tags
		special_tag_match = regex.search(r'^(?:\{[^\}]+\})?(\w+)$', node.tag)
		if special_tag_match and special_tag_match.group(1) in ["img"]:
			span = etree.Element("{%s}span" % ("http://www.w3.org/1999/xhtml", ), attrib={"id": "kobo.{0}.{1}".format(paragraph_counter, segment_counter), "class": "koboSpan"})
			span.append(node)
			return span

		# Save node content for later
		nodetext = node.text
		nodechildren = deepcopy(node.getchildren())
		nodeattrs = {}
		for key in node.keys():
			nodeattrs[key] = node.get(key)

		# Reset current node, to start from scratch
		node.clear()

		# Restore node attributes
		for key in nodeattrs.keys():
			node.set(key, nodeattrs[key])

		# The node text is converted to spans
		if nodetext is not None:
			if not append_kobo_spans_from_text(node, nodetext):
				# didn't add spans, restore text
				node.text = nodetext

		# Re-add the node children
		for child in nodechildren:
			# Save child tail for later
			childtail = child.tail
			child.tail = None
			node.append(add_kobo_spans_to_node(child))
			# The child tail is converted to spans
			if childtail is not None:
				paragraph_counter += 1
				segment_counter = 1
				if not append_kobo_spans_from_text(node, childtail):
					# Didn't add spans, restore tail on last child
					paragraph_counter -= 1
					node[-1].tail = childtail

			paragraph_counter += 1
			segment_counter = 1
	else:
		node.tail = None
	return node
