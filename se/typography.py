#!/usr/bin/env python3
"""
Defines various typography-related functions
"""

import html
from typing import Optional, Union
import unicodedata

import pyphen
import regex
import smartypants

import se
from se.easy_xml import EasyXmlTree


def _number_to_fraction(string: str) -> str:
	"""
	Helper function to convert a regular fraction string to a
	Unicode superscript/subscript fraction.

	Example:
	4/19 -> ⁴⁄₁₉
	"""

	output = ""
	in_numerator = True

	try:
		for char in string:
			if char == "/":
				# Fraction slash, not solidus
				output = output + "⁄"
				in_numerator = False
			else:
				if 0 <= int(char) <= 9:
					if in_numerator:
						# Convert to superscript
						# superscript 0-3 are exceptions
						if char == "0":
							output = output + "⁰"
						elif char == "1":
							output = output + "¹"
						elif char == "2":
							output = output + "²"
						elif char == "3":
							output = output + "³"
						else:
							output = output + chr(ord(char) + 8256)
					else:
						# Convert to subscript
						output = output + chr(ord(char) + 8272)
				else:
					output = output + char
	except Exception:
		return string

	return output

def typogrify(xhtml: str, smart_quotes: bool = True) -> str:
	"""
	Typogrify a string of XHTML according to SE house style.

	INPUTS
	xhtml: A string of well-formed XHTML.
	smart_quotes: True to convert straight quotes to curly quotes.

	OUTPUTS
	A string of typogrified XHTML.
	"""

	# For information on Unicode line breaks, see https://www.unicode.org/reports/tr14/tr14-37.html

	if smart_quotes:
		# Some Gutenberg works have a weird single quote style: `this is a quote'.  Clean that up here before running Smartypants.
		xhtml = xhtml.replace("`", "'")

		# First, convert entities.  Sometimes Gutenberg has entities instead of straight quotes.
		xhtml = html.unescape(xhtml) # This converts html entities to unicode
		xhtml = regex.sub(r"&(?![#\p{Lowercase_Letter}]+;)", "&amp;", xhtml) # Oops!  html.unescape also unescapes plain ampersands...

		# Replace rsquo character with an escape sequence. We can't use HTML comments
		# because rsquo may appear inside alt attributes, and that would break smartypants.
		# When we encounter an actual rsquo, it's 99% correct as-is.
		xhtml = xhtml.replace("’", "!#se:rsquo#!")

		xhtml = smartypants.smartypants(xhtml) # Attr.u *should* output unicode characters instead of HTML entities, but it doesn't work

		# Convert entities again
		xhtml = html.unescape(xhtml) # This converts html entities to unicode
		xhtml = regex.sub(r"&(?![#\p{Lowercase_Letter}]+;)", "&amp;", xhtml) # Oops!  html.unescape also unescapes plain ampersands...

	# Replace no-break hyphen with regular hyphen
	# We don't do this anymore and leave this check to `se find-unusual-characters`
	# xhtml = xhtml.replace(se.NO_BREAK_HYPHEN, "-")

	# Replace horizontal bar with em dash
	xhtml = xhtml.replace("―", "—")

	# Replace sequential em dashes with the two or three em dash character
	xhtml = xhtml.replace("———", "⸻")
	xhtml = xhtml.replace("——", "⸺")

	# Smartypants doesn't do well on em dashes followed by open quotes. Fix that here
	xhtml = regex.sub(r"—”([\p{Letter}])", r"—“\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"—’([\p{Letter}])", r"—‘\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"-“</p>", r"—”</p>", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"‘”</p>", fr"’{se.HAIR_SPACE}”</p>", xhtml, flags=regex.IGNORECASE)

	# Now that we've fixed Smartypants' output, put our quotes back in
	xhtml = xhtml.replace("!#se:rsquo#!", "’")

	# Remove spaces between en and em dashes
	# Note that we match at least one character before the dashes, so that we don't catch start-of-line em dashes like in poetry.
	# We do a negative lookbehind for <br/ to prevent newlines/indents after <br/>s from being included
	xhtml = regex.sub(r"(?<!<br/)([^\.…\s])\s*([–—])\s*", r"\1\2", xhtml, flags=regex.DOTALL)

	# First, remove stray word joiners
	xhtml = xhtml.replace(se.WORD_JOINER, "")

	# Remove shy hyphens
	xhtml = xhtml.replace(se.SHY_HYPHEN, "")

	# Fix some common em-dash transcription errors
	xhtml = regex.sub(r"([:;])-([\p{Letter}])", r"\1—\2", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([\p{Letter}])-“", r"\1—“", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r":-</", fr":{se.WORD_JOINER}—</", xhtml)

	# Em dashes and two-em-dashes can be broken before, so add a word joiner between letters/punctuation and the following em dash
	xhtml = regex.sub(fr"([^\s{se.WORD_JOINER}{se.NO_BREAK_SPACE}{se.HAIR_SPACE}])([—⸻])", fr"\1{se.WORD_JOINER}\2", xhtml, flags=regex.IGNORECASE)

	# Add en dashes; don't replace match that is within an html tag, since ids and attrs often contain the pattern DIGIT-DIGIT
	xhtml = regex.sub(r"(?<!<[^>]*)([0-9]+)\-([0-9]+)", r"\1–\2", xhtml)

	# Add a word joiner on both sides of en dashes
	xhtml = regex.sub(fr"{se.WORD_JOINER}?–{se.WORD_JOINER}?", fr"{se.WORD_JOINER}–{se.WORD_JOINER}", xhtml)

	# Add a word joiner if eliding a word with a two-em-dash
	# Word joiner isn't necessary if punctuation follows
	# Note the \p{{P}}.  We must double-curl {} because that's the escape sequence when using .format().  The actual regex should be \p{P} to match punctuation
	xhtml = regex.sub(fr"([^\s{se.WORD_JOINER}{se.NO_BREAK_SPACE}{se.HAIR_SPACE}])⸺", fr"\1{se.WORD_JOINER}⸺", xhtml)
	xhtml = regex.sub(fr"⸺([^\s\p{{P}}{se.WORD_JOINER}])", fr"⸺{se.WORD_JOINER}\1", xhtml)

	# Add a space between text and —th, which is usually an obscured number. I.e. "The —th battalion"
	xhtml = regex.sub(fr"([\p{{Lowercase_Letter}}]){se.WORD_JOINER}—th\b", r"\1 —th", xhtml)

	# Remove word joiners from following opening tags--they're usually never correct
	xhtml = regex.sub(fr"<([\p{{Letter}}]+)([^>]*?)>{se.WORD_JOINER}", r"<\1\2>", xhtml, flags=regex.IGNORECASE)

	# Add a word joiner after em dashes within <cite> elements
	xhtml = regex.sub(r"<cite([^>]*?)>—", fr"<cite\1>—{se.WORD_JOINER}", xhtml)

	# Finally fix some other mistakes
	xhtml = xhtml.replace("—-", "—")

	# Possessives after inline elements need to be corrected after Smartypants
	xhtml = regex.sub(r"</(i|em|b|strong|q|span)>‘(s|d)", r"</\1>’\2", xhtml)

	# Replace two-em-dashes with an em-dash, but try to exclude ones being used for elision
	xhtml = regex.sub(fr"([I\p{{Lowercase_Letter}}>\.\?\!,’]{se.WORD_JOINER})⸺”", r"\1—”", xhtml)
	xhtml = regex.sub(fr"([^\s‘“—][a-z\.]{se.WORD_JOINER})⸺\s?", r"\1—", xhtml)

	# Some older texts use the ,— construct; remove that archaism
	xhtml = regex.sub(fr",({se.WORD_JOINER}?)—", r"\1—", xhtml)

	# Remove spaces after two-em-dashes that do not appear to be elision
	xhtml = regex.sub(fr"(\p{{Letter}}{{2,}}{se.WORD_JOINER})⸺\s", r"\1—", xhtml)

	# Dash before closing double quote in clauses with more than two words is almost always a typo
	xhtml = regex.sub(r"(“[^<]+?\s[^<]+?)-”", fr"\1{se.WORD_JOINER}—”", xhtml)

	# Replace Mr., Mrs., and other abbreviations, and include a non-breaking space
	xhtml = regex.sub(r"\b(Mr|Mr?s|Drs?|Profs?|Lieut|Fr|Lt|Capt|Pvt|Esq|Mt|St|MM|Mmes?|Mlles?|Hon|Mdlle)\.?(</abbr>)?\s+", fr"\1.\2{se.NO_BREAK_SPACE}", xhtml)

	# Include a non-breaking space after Mon. We can't include it in the above regex because `Mon` may appear as running French language (i.e. `Mon Dieu`)
	xhtml = regex.sub(r"\bMon\.(</abbr>)?\s+", fr"Mon.\1{se.NO_BREAK_SPACE}", xhtml)

	# \P{} is the inverse of \p{}, so this regex matches any of the abbrs followed by any punctuation except a period. We also 'or' against a word joiner,
	# in case Mr. is run up against an em dash.
	xhtml = regex.sub(fr"\b(Mr|Mr?s|Drs?|Profs?|Lieut|Fr|Lt|Capt|Pvt|Esq|Mt|St|MM|Mmes?|Mlles?)\.?(</abbr>)?([^\P{{Punctuation}}\.]|{se.WORD_JOINER})", r"\1.\2\3", xhtml)

	# We added an nbsp after St. above. But, sometimes a name can be abbreviated, like `Bob St. M.`. In this case we don't want an nbsp because <abbr> is already `white-space: nowrap;`.
	xhtml = regex.sub(fr"""<abbr epub:type="(z3998:[^"\s]+?name)">St\.{se.NO_BREAK_SPACE}([A-Z])""", r"""<abbr epub:type="\1">St. \2""", xhtml)

	xhtml = regex.sub(r"\bNo\.\s+([0-9]+)", fr"No.{se.NO_BREAK_SPACE}\1", xhtml)
	xhtml = regex.sub(r"<abbr>No\.</abbr>\s+", fr"<abbr>No.</abbr>{se.NO_BREAK_SPACE}", xhtml)

	xhtml = regex.sub(r"([0-9]+)\s<abbr", fr"\1{se.NO_BREAK_SPACE}<abbr", xhtml)

	xhtml = regex.sub(r"c/o", "℅", xhtml, flags=regex.IGNORECASE)

	# Sort out preceding rsquos for  `tis` / `twas` / `twere` / `twont’t`
	# 1. If there’s a missing quote (after a space or tag) add it.
	# 2. If there’s a right double-quote assumed it should be an open and closing single quote pair.
	contractions = r"[Tt]is|[Tt]was|[Tt]were|[Tt]won’t"
	xhtml = regex.sub(fr"([\s>])({ contractions })\b", r"\1’\2", xhtml) # 1.
	xhtml = regex.sub(fr"”\b({ contractions })\b", r"‘’\1", xhtml)      # 2.

	# Replace `M‘<letter>` with `Mc<letter>`; use of lsquo in this case is a historical case of a "poor man's superscript c". See
	# https://english.stackexchange.com/questions/543272/why-were-scottish-irish-names-once-rendered-with-apostrophes-instead-of-mac#543329
	xhtml = regex.sub(r"\bM‘([\p{Uppercase_Letter}][\p{Letter}]+?)", r"Mc\1", xhtml)

	# A note on spacing:
	# 					ibooks	kindle (mobi7)
	# thin space U+2009:			yes	yes
	# word joiner U+2060:			no	yes
	# zero-width no-break space U+FEFF:	yes	yes
	# narrow no-break space U+202F:		no	yes
	# punctuation space U+2008:		yes	yes

	# Fix common abbreviatons
	xhtml = regex.sub(r"(\s)‘a’(\s)", r"\1’a’\2", xhtml, flags=regex.IGNORECASE)

	# Years
	xhtml = regex.sub(r"‘([0-9]{2,}[^\p{Letter}0-9’])", r"’\1", xhtml, flags=regex.IGNORECASE)

	xhtml = regex.sub(r"‘([Aa]ve|[Oo]me|[Ii]m|[Mm]idst|[Gg]ainst|[Nn]eath|[Ee]m|[Cc]os|[Tt]is|[Tt]isn’t|[Tt]was|[Tt]ain’t|[Tt]wixt|[Tt]were|[Tt]would|[Tt]wouldn|[Tt]won|[Tt]ween|[Tt]will|[Rr]ound|[Pp]on|[Uu]ns?|[Uu]d|[Cc]ept|[Oo]w|[Aa]ppen|[Ee])\b", r"’\1", xhtml)

	xhtml = regex.sub(r"\b‘e\b", r"’e", xhtml)
	xhtml = regex.sub(r"\b‘([Ee])r\b", r"’\1r", xhtml)
	xhtml = regex.sub(r"\b‘([Ee])re\b", r"’\1re", xhtml)
	xhtml = regex.sub(r"\b‘([Aa])ppen\b", r"’\1ppen", xhtml)
	xhtml = regex.sub(r"\b‘([Aa])ven\b", r"’\1ven", xhtml) #  'aven't

	# nth (as in nth degree)
	xhtml = regex.sub(r"\bn\-?th\b", r"<i>n</i>th", xhtml)

	# Remove double spaces that use se.NO_BREAK_SPACE for spacing
	xhtml = regex.sub(fr"{se.NO_BREAK_SPACE}[{se.NO_BREAK_SPACE} ]+", r" ", xhtml)
	xhtml = regex.sub(fr" [{se.NO_BREAK_SPACE} ]+", r" ", xhtml)

	# House style: remove spacing from common Latinisms
	xhtml = regex.sub(r"([Ii])\.\s+e\.", r"\1.e.", xhtml)
	xhtml = regex.sub(r"([Ee])\.\s+g\.", r"\1.g.", xhtml)

	# Remove nbsps between words
	xhtml = regex.sub(fr"([^>…]){se.NO_BREAK_SPACE}([\p{{Letter}}\p{{Digit}}])", r"\1 \2", xhtml)

	# Add nbsp before `De` last names, but not Latin titles like `<i xml:lang="la">De Natura</i>`
	xhtml = regex.sub(r"([^>])De ([A-Z][a-z]+?)", fr"\1De{se.NO_BREAK_SPACE}\2", xhtml)

	# WARNING! This and below can remove the ending period of a sentence, if AD or BC is the last word!  We need interactive S&R for this
	xhtml = regex.sub(r"([\d\s])A\.\s+D\.", r"\1AD", xhtml)
	xhtml = regex.sub(r"(?<!A\. )B\.\s+C\.", r"BC", xhtml)

	# Put spacing next to close quotes
	xhtml = regex.sub(fr"“[\s{se.NO_BREAK_SPACE}]*‘", fr"“{se.HAIR_SPACE}‘", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"’[\s{se.NO_BREAK_SPACE}]*”", fr"’{se.HAIR_SPACE}”", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"“[\s{se.NO_BREAK_SPACE}]*’", fr"“{se.HAIR_SPACE}’", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"‘[\s{se.NO_BREAK_SPACE}]*“", fr"‘{se.HAIR_SPACE}“", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"‘[\s{se.NO_BREAK_SPACE}]*’", fr"‘{se.HAIR_SPACE}’", xhtml, flags=regex.IGNORECASE)

	# We require a non-letter char at the end, otherwise we might match a contraction: “Hello,” ’e said.
	xhtml = regex.sub(fr"”[\s{se.NO_BREAK_SPACE}]*’([^\p{{Letter}}])", fr"”{se.HAIR_SPACE}’\1", xhtml, flags=regex.IGNORECASE)

	# Fix ellipses spacing
	xhtml = regex.sub(r"\s*\.\s*\.\s*\.\s*", r"…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"[\s{se.NO_BREAK_SPACE}]?…[\s{se.NO_BREAK_SPACE}]?\.", fr".{se.HAIR_SPACE}…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"[\s{se.NO_BREAK_SPACE}]?…[\s{se.NO_BREAK_SPACE}]?", fr"{se.HAIR_SPACE}… ", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"<p([^>]*?)>{se.HAIR_SPACE}…", r"<p\1>…", xhtml, flags=regex.IGNORECASE)

	# Remove spaces between opening tags and ellipses
	xhtml = regex.sub(fr"(<[\p{{Letter}}0-9]+[^<]+?>)[\s{se.NO_BREAK_SPACE}]+?…", r"\1…", xhtml, flags=regex.IGNORECASE)

	# Remove spaces between closing tags and ellipses
	xhtml = regex.sub(fr"…[\s{se.NO_BREAK_SPACE}]?(</[\p{{Letter}}0-9]+>)", r"…\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"…[\s{se.NO_BREAK_SPACE}]+([\)”’])(?![\p{{Letter}}])", r"…\1", xhtml, flags=regex.IGNORECASE) # If followed by a letter, the single quote is probably a leading elision
	xhtml = regex.sub(fr"([\(“‘])[\s{se.NO_BREAK_SPACE}]+…", r"\1…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"…[\s{se.NO_BREAK_SPACE}]?([\!\?\.\;\,])", fr"…{se.HAIR_SPACE}\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"([\!\?\.\;”’])[\s{se.NO_BREAK_SPACE}]?…", fr"\1{se.HAIR_SPACE}…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(fr"\,[\s{se.NO_BREAK_SPACE}]?…", fr",{se.HAIR_SPACE}…", xhtml, flags=regex.IGNORECASE)

	# Add nbsp to ellipses that open dialog
	xhtml = regex.sub(r"([“‘])…\s([\p{Letter}0-9])", fr"\1…{se.NO_BREAK_SPACE}\2", xhtml, flags=regex.IGNORECASE)

	# Don't use . ... if within a clause
	xhtml = regex.sub(r"\.(\s…\s[\p{Lowercase_Letter}])", r"\1", xhtml)

	# Remove period from . .. if after punctuation
	xhtml = regex.sub(r"([\!\?\,\;\:]\s*)\.(\s…)", r"\1\2", xhtml)

	# Remove a point from four-point ellipses from beginning of paragraph
	xhtml = regex.sub(r"<p>\. …", "<p>…", xhtml)

	# Add non-breaking spaces between amounts with an abbreviated unit.  E.g. 8 oz., 10 lbs.
	# Don't generalize this to match letters because it will add too many false positives
	xhtml = regex.sub(r"([0-9])\s+(oz\.|lbs\.)", fr"\1{se.NO_BREAK_SPACE}\2", xhtml, flags=regex.IGNORECASE)

	# Add non-breaking spaces between Arabic numbers and AM/PM
	xhtml = regex.sub(r"([0-9])\s+([ap])\.m\.", fr"\1{se.NO_BREAK_SPACE}\2.m.", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([0-9])\s+<abbr([^>]*?)>([ap])\.m\.", fr"\1{se.NO_BREAK_SPACE}<abbr\2>\3.m.", xhtml, flags=regex.IGNORECASE)

	xhtml = regex.sub(r"P\.?\s*S\.", r"P.S.", xhtml)

	# Fractions (ensure no leading/trailing slashes to prevent converting dates)
	xhtml = regex.sub(r"\b(?<!/)1/4(?!/)\b", "¼", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/2(?!/)\b", "½", xhtml)
	xhtml = regex.sub(r"\b(?<!/)3/4(?!/)\b", "¾", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/7(?!/)\b", "⅐", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/9(?!/)\b", "⅑", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/10(?!/)\b", "⅒", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/3(?!/)\b", "⅓", xhtml)
	xhtml = regex.sub(r"\b(?<!/)2/3(?!/)\b", "⅔", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/5(?!/)\b", "⅕", xhtml)
	xhtml = regex.sub(r"\b(?<!/)2/5(?!/)\b", "⅖", xhtml)
	xhtml = regex.sub(r"\b(?<!/)3/5(?!/)\b", "⅗", xhtml)
	xhtml = regex.sub(r"\b(?<!/)4/5(?!/)\b", "⅘", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/6(?!/)\b", "⅙", xhtml)
	xhtml = regex.sub(r"\b(?<!/)5/6(?!/)\b", "⅚", xhtml)
	xhtml = regex.sub(r"\b(?<!/)1/8(?!/)\b", "⅛", xhtml)
	xhtml = regex.sub(r"\b(?<!/)3/8(?!/)\b", "⅜", xhtml)
	xhtml = regex.sub(r"\b(?<!/)5/8(?!/)\b", "⅝", xhtml)
	xhtml = regex.sub(r"\b(?<!/)7/8(?!/)\b", "⅞", xhtml)

	# Convert any remaining fractions to use the fraction slash
	# Don't match possible years, like 1945/6, 1945/46, 1945/1946
	xhtml = regex.sub(r"\b(?<!/)([0-9]{1,3}|[0-9]{5,})/\b([0-9]{1,3}|[0-9]{5,})(?!/)\b", lambda result: _number_to_fraction(result.group(0)), xhtml)

	# Remove spaces between whole numbers and fractions
	xhtml = regex.sub(r"([0-9,]+)\s+([¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞]|[⁰¹²³⁴⁵⁶⁷⁸⁹]+⁄[₀₁₂₃₄₅₆₇₈₉]+)", r"\1\2", xhtml)

	# Use the Unicode Minus glyph (U+2212) for negative numbers
	xhtml = regex.sub(r"([\s>])\-([0-9,]+)", r"\1−\2", xhtml)

	# Convert L to £ if next to a number
	xhtml = regex.sub(r"\bL([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)", r"£\1", xhtml)

	# Make sure there are periods after old-style shilling/pence denominations
	xhtml = regex.sub(r"\b([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)s\.? ([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)d\.?", r"\1s. \2d.", xhtml)

	# Remove periods after pounds if followed by shillings
	xhtml = regex.sub(r"£([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)\.? ([0-9½¼¾⅙⅚⅛⅜⅝⅞]+)s\.?", r"£\1 \2s.", xhtml)

	# Remove word joiners if the em dash is preceded by a space
	xhtml = regex.sub(fr"(\s+){se.WORD_JOINER}—", r"\1—", xhtml)

	# Fix some common error cases
	xhtml = regex.sub(r"‘n’", "’n’", xhtml)
	xhtml = regex.sub(r"</(a|abbr|b|i|span)>‘(s|d)\b", r"</\1>’\2", xhtml)

	# Remove periods from O.K. (also, it is not an abbreviation)
	xhtml = regex.sub(r"O\.K\.", r"OK", xhtml)
	xhtml = regex.sub(r"OK([”’]\s+[\p{Uppercase_Letter}])", r"OK.\1", xhtml)
	xhtml = regex.sub(r"(“[^”]+?)OK ([\p{Uppercase_Letter}]\w+)", r"\1OK.” \2", xhtml)

	# Add an &nbsp; before &amp;
	xhtml = regex.sub(r" &amp;", f"{se.NO_BREAK_SPACE}&amp;", xhtml)

	# Add word joiners to ellipses
	xhtml = regex.sub(fr"{se.HAIR_SPACE}…", f"{se.WORD_JOINER}{se.HAIR_SPACE}{se.WORD_JOINER}…", xhtml)

	# Remove any extra spaces in 4-dot ellipses that occur before the starting period
	xhtml = regex.sub(fr"([\p{{Letter}}]){se.HAIR_SPACE}(\.{se.WORD_JOINER}{se.HAIR_SPACE}{se.WORD_JOINER}…)", r"\1\2", xhtml)

	# Remove spaces between ellipses and endnotes directly after
	xhtml = regex.sub(fr"…[\s{se.NO_BREAK_SPACE}]?(<a[^>]+?epub:type=\"noteref\"[^>]*?>)", r"…\1", xhtml, flags=regex.IGNORECASE)

	# Remove word joiners and nbsp from img alt attributes
	for match in regex.findall(fr"alt=\"[^\"]*?[{se.NO_BREAK_SPACE}{se.WORD_JOINER}][^\"]*?\"", xhtml):
		xhtml = xhtml.replace(match, match.replace(se.NO_BREAK_SPACE, " ").replace(se.WORD_JOINER, ""))

	# Remove word joiners and nbsp from <title> elements
	for match in regex.findall(fr"<title>[^<]*?[{se.NO_BREAK_SPACE}{se.WORD_JOINER}][^<]*?</title>", xhtml):
		xhtml = xhtml.replace(match, match.replace(se.NO_BREAK_SPACE, " ").replace(se.WORD_JOINER, ""))

	# Remove no-break spaces added before etc.
	xhtml = regex.sub(fr"{se.NO_BREAK_SPACE}(<abbr[^>]*?>etc\.)", r" \1", xhtml)

	return xhtml

def hyphenate(xhtml: Union[str, EasyXmlTree], language: Optional[str], ignore_h_tags: bool = False) -> str:
	"""
	Add soft hyphens to a string of XHTML.

	INPUTS
	xhtml: A string of XHTML
	language: An ISO language code, like en-US, or None to auto-detect based on XHTML input
	ignore_h_tags: True to not hyphenate within <h1-6> tags

	OUTPUTS
	A string of XHTML with soft hyphens inserted in words. The output is not guaranteed to be pretty-printed.
	"""

	output_xhtml = ""

	if isinstance(xhtml, EasyXmlTree):
		dom = xhtml
		output_xhtml = dom.to_string()
	else:
		dom = EasyXmlTree(xhtml)
		output_xhtml = xhtml

	if language is None:
		try:
			language = dom.xpath("/html/@xml:lang | /html/@lang")[0]
		except Exception as ex:
			raise se.InvalidLanguageException("No [attr]xml:lang[/] or [attr]lang[/] attribute on [xhtml]<html>[/] element; couldn’t guess file language.") from ex

	# Cope with known missing languages
	if language in ["en-AU", "en-CA", "en-IE"] :
		language = "en-GB"

	language = language.replace("-", "_")

	if language not in pyphen.LANGUAGES:
		raise se.MissingDependencyException(f"Hyphenator for language [text]{language}[/] not available.\nInstalled hyphenators: {pyphen.LANGUAGES}.")

	hyphenator = pyphen.Pyphen(lang=language)

	text = dom.xpath("/html/body")[0].inner_xml()
	result = ""
	word = ""
	in_tag = False
	tag_name = ""
	reading_tag_name = False
	in_h_tag = False

	# The general idea here is to read the whole contents of the <body> tag character by character.
	# If we hit a <, we ignore the contents until we hit the next >.
	# Otherwise, we consider a word to be an unbroken sequence of alphanumeric characters.
	# We can't just split at whitespace because HTML tags can contain whitespace (attributes for example)
	for char in text:
		process = False
		reading_word = False

		if char == "<":
			process = True
			in_tag = True
			reading_tag_name = True
			tag_name = ""
		elif in_tag and char == ">":
			in_tag = False
			reading_tag_name = False
			word = ""
		elif in_tag and char == " ":
			reading_tag_name = False
		elif in_tag and reading_tag_name:
			tag_name = tag_name + char
		elif not in_tag and char.isalnum():
			word = word + char
			reading_word = True
		elif not in_tag:
			process = True

		# Do we ignore <h1-6> tags?
		if not reading_tag_name and regex.match(r"^h[1-6]$", tag_name):
			in_h_tag = True

		if not reading_tag_name and regex.match(r"^/h[1-6]$", tag_name):
			in_h_tag = False

		if ignore_h_tags and in_h_tag:
			process = False

		if process:
			if word != "":
				new_word = hyphenator.inserted(word, hyphen=se.SHY_HYPHEN)
				result = result + new_word + char
			else:
				result = result + char

			word = ""
		elif not reading_word or (in_h_tag and ignore_h_tags):
			result = result + char

	# We need to double-escape backslashes in the replacement string, in case the string contains a backslash+number that
	# the regex engine will misinterpret as a capture group
	output_xhtml = regex.sub(r"(<body[^>]*?>).+</body>", r"\1" + result.replace("\\", "\\\\") + "</body>", output_xhtml, flags=regex.DOTALL)

	return output_xhtml

def guess_quoting_style(xhtml: str) -> str:
	"""
	Guess whether the passed XHTML quotation is British or American style.

	INPUTS
	xhtml: A string of XHTML

	OUTPUTS
	A string containing one of these three values: "british", "american", or "unsure"
	"""

	# Want to discover the first quote type after a <p> tag. Doesn't have to be
	# directly after.

	# Count pattern matches for each quote style (disregard matches where the
	# capturing group contains opposite quote style).

	# Quote style percentage above the threshold is returned.
	threshold = 80

	ldq_count = len([m for m in regex.findall(r"\t*<p[^>]*>(.*?)“", xhtml) if m.count("‘") == 0])
	lsq_count = len([m for m in regex.findall(r"\t*<p[^>]*>(.*?)‘", xhtml) if m.count("“") == 0])
	detected_style = "unsure"

	if (ldq_count + lsq_count) != 0:
		american_percentage = int((ldq_count / (ldq_count + lsq_count)) * 100)
		british_percentage = int((lsq_count / (ldq_count + lsq_count)) * 100)

		if american_percentage >= threshold:
			detected_style = "american"
		elif british_percentage >= threshold:
			detected_style = "british"

	return detected_style

def convert_british_to_american(xhtml: str) -> str:
	"""
	Attempt to convert a string of XHTML from British-style quotation to American-style quotation.

	INPUTS
	xhtml: A string of XHTML

	OUTPUTS
	The XHTML with British-style quotation converted to American style
	"""
	xhtml = regex.sub(r"“", r"<ldq>", xhtml)
	xhtml = regex.sub(r"”", r"<rdq>", xhtml)
	xhtml = regex.sub(r"‘", r"<lsq>", xhtml)
	xhtml = regex.sub(r"<rdq>⁠ ’(\s+)", r"<rdq> <rsq>\1", xhtml)
	xhtml = regex.sub(r"<rdq>⁠ ’</", r"<rdq> <rsq></", xhtml)
	xhtml = regex.sub(r"([\.\,\!\?\…\:\;])’", r"\1<rsq>", xhtml)
	xhtml = regex.sub(r"—’(\s+)", r"—<rsq>\1", xhtml)
	xhtml = regex.sub(r"—’</", r"—<rsq></", xhtml)
	xhtml = regex.sub(r"([\p{Lowercase_Letter}])’([\p{Lowercase_Letter}])", r"\1<ap>\2", xhtml)
	xhtml = regex.sub(r"(\s+)’([\p{Lowercase_Letter}])", r"\1<ap>\2", xhtml)
	xhtml = regex.sub(r"<ldq>", r"‘", xhtml)
	xhtml = regex.sub(r"<rdq>", r"’", xhtml)
	xhtml = regex.sub(r"<lsq>", r"“", xhtml)
	xhtml = regex.sub(r"<rsq>", r"”", xhtml)
	xhtml = regex.sub(r"<ap>", r"’", xhtml)

	# Correct some common errors
	xhtml = regex.sub(r"’ ’", r"’ ”", xhtml)
	xhtml = regex.sub(r"“([^‘”]+?[^s])’([!\?:;\)\s])", r"“\1”\2", xhtml)
	xhtml = regex.sub(r"“([^‘”]+?)’([!\?:;\)])", r"“\1”\2", xhtml)

	return xhtml


def normalize_greek(text: str) -> str:
	"""
	Given a string of supposed Greek text, return a normalized version
	that attempts to correct some common transcription errors.
	A better check would be:
		`regex.match(r"\\p{Script=Latin}", "τŵν")`
	but Python doesn't support `script=` in regex yet. For a potential workaround see:
		https://stackoverflow.com/questions/9868792/find-out-the-unicode-script-of-a-character

	Also see:
		https://github.com/standardebooks/plato_dialogues_benjamin-jowett/pull/4
		https://github.com/standardebooks/herman-melville_moby-dick/issues/12
		https://jktauber.com/articles/python-unicode-ancient-greek/
		https://www.unicode.org/faq/greek.html
		http://www.opoudjis.net/unicode/unicode.html
	"""

	table = [
		('\u0302', '\u0342'), # circumflex -> perispomeni
		('\u0323', '\u0345'), # dot below -> ypogegrammeni
		('a', 'α'),
		('i', 'ι'),
		('ɩ', 'ι'), # Latin iota -> Greek iota
		('o', 'ο'), # Latin o -> Greek omicron
		('w', 'ω'),
		(r'ν(?=\p{Mn})', 'υ'),
		('\u0020\u0313', '’'), # non-spacing psili -> space + comma above -> apostrophe
	]

	mark_order = {
		'\u0313': -1, # comma above
		'\u0314': -1, # reversed comma above
		'\u0345': 1, # ypogegrammeni
	}

	expected_contents = unicodedata.normalize('NFKC', text)
	for wrong_char, correct_char in table:
		expected_contents = regex.sub(wrong_char, correct_char, expected_contents)

	expected_contents = regex.sub(r'\p{Mn}+',
		lambda marks: ''.join(
			[m for _, m in sorted(
				[(mark_order.get(m, 0), m) for m in marks.group()],
				key=lambda x: x[0]
			)]
	), expected_contents)

	expected_contents = unicodedata.normalize('NFC', expected_contents)

	# Unicode normalization changes `…` to `...`, and also `hairsp` to `space`, so change those back
	expected_contents = expected_contents.replace("⁠ ⁠...", "⁠ ⁠…")
	expected_contents = expected_contents.replace("... ", "… ")

	return expected_contents
