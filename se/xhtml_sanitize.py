"""
XHTML sanitization utilities for handling OCR-damaged text.

Internet Archive EPUBs and other OCR sources frequently contain text that
breaks strict XML parsing:

- Bare '<' characters from garbled scans (e.g., "4<th battalion", "S < w")
- Unclosed HTML5 void elements (<img>, <br> without self-closing slash)
- Characters that look like unquoted HTML attributes

This module provides a sanitizer that fixes these issues so the text can
be parsed as valid XHTML while preserving all legitimate markup.
"""

import re
from xml.etree.ElementTree import ParseError as XMLParseError
from xml.etree.ElementTree import fromstring as xml_parse


# HTML5 void elements that must be self-closing in XHTML
VOID_TAGS = frozenset({
	"img", "br", "hr", "input", "meta", "link", "col",
	"area", "base", "embed", "source", "track", "wbr",
})


def sanitize_xhtml(xhtml: str) -> str:
	"""
	Sanitize XHTML content to fix common OCR-induced XML errors.

	Uses a character-level scanner that distinguishes real tags from OCR
	noise by checking the full tag structure:

	1. A '<' followed by a valid tag name AND proper tag syntax (attributes,
	   closing '>') is left alone.
	2. A '<' followed by something that never reaches a closing '>' (or hits
	   another '<' first) is escaped to '&lt;'.
	3. Void elements without self-closing slashes get '/' added.

	This handles OCR fragments like "4<th battalion" (the '<th' never closes
	properly), "S < w" (space after '<'), and "<>2" (empty tag).

	If the input already parses as valid XML, it is returned unchanged.
	"""

	# Fast path: if it's already valid, don't touch it
	try:
		xml_parse(xhtml)
		return xhtml
	except XMLParseError:
		pass

	result: list[str] = []
	i = 0
	n = len(xhtml)

	while i < n:
		if xhtml[i] != "<":
			result.append(xhtml[i])
			i += 1
			continue

		rest = xhtml[i + 1:i + 200]

		# End of string
		if not rest:
			result.append("&lt;")
			i += 1
			continue

		# Comment (<!--) or doctype (<!DOCTYPE)
		if rest[0] == "!":
			result.append("<")
			i += 1
			continue

		# Processing instruction (<?)
		if rest[0] == "?":
			result.append("<")
			i += 1
			continue

		# Closing tag (</tagname>)
		if rest[0] == "/":
			if re.match(r"/([a-zA-Z][a-zA-Z0-9]*)\s*>", rest):
				result.append("<")
				i += 1
				continue
			# Malformed closing tag — escape
			result.append("&lt;")
			i += 1
			continue

		# Opening tag candidate: <tagname...>
		tag_start = re.match(r"([a-zA-Z][a-zA-Z0-9]*)", rest)
		if tag_start:
			tag_name = tag_start.group(1)
			after_name = rest[len(tag_name):]

			# After tag name, must see >, />, or whitespace (for attributes)
			if after_name and after_name[0] in (">", "/", " ", "\t", "\n", "\r"):
				# Scan forward to find the closing '>' for this tag,
				# skipping quoted attribute values
				j = i + 1 + len(tag_name)
				in_quote: str | None = None
				found_close = False

				while j < n:
					c = xhtml[j]
					if in_quote:
						if c == in_quote:
							in_quote = None
					elif c in ('"', "'"):
						in_quote = c
					elif c == ">":
						found_close = True
						break
					elif c == "<":
						# Hit another '<' before closing — not a real tag
						break
					j += 1

				if found_close:
					tag_content = xhtml[i:j + 1]
					tag_lower = tag_name.lower()

					# Fix void elements missing self-closing slash
					if tag_lower in VOID_TAGS and not tag_content.endswith("/>"):
						result.append(tag_content[:-1] + "/>")
					else:
						result.append(tag_content)

					i = j + 1
					continue

			# Tag name found but no proper tag structure follows — escape
			result.append("&lt;")
			i += 1
			continue

		# '<' not followed by a letter, /, !, or ? — escape
		result.append("&lt;")
		i += 1

	return "".join(result)


def strip_ocr_noise(text: str) -> str:
	"""
	Remove Internet Archive OCR confidence lines and other machine-generated
	noise from text content.
	"""

	# IA OCR accuracy estimates
	text = re.sub(
		r"(?m)^\s*The text on this page is estimated to be only [\d.]+% accurate\s*$",
		"",
		text,
	)

	# IA hocr-to-epub version stamps
	text = re.sub(r"(?m)^\s*Created with hocr-to-epub\b.*$", "", text)

	return text
