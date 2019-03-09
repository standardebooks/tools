#!/usr/bin/env python3
"""
Defines various typography-related functions
"""

import html
import regex
import smartypants
from hyphen import Hyphenator
from hyphen.dictools import list_installed
from bs4 import BeautifulSoup
import se


def typogrify(xhtml: str, smart_quotes: bool = True) -> str:
	"""
	Typogrify a string of XHTML according to SE house style.

	INPUTS
	xhtml: A string of well-formed XHTML.
	smart_quotes: True to convert straight quotes to curly quotes.

	OUTPUTS
	A string of typogrified XHTML.
	"""

	if smart_quotes:
		# Some Gutenberg works have a weird single quote style: `this is a quote'.  Clean that up here before running Smartypants.
		xhtml = xhtml.replace("`", "'")

		# First, convert entities.  Sometimes Gutenberg has entities instead of straight quotes.
		xhtml = html.unescape(xhtml) # This converts html entites to unicode
		xhtml = regex.sub(r"&([^#a-z])", r"&amp;\1", xhtml) # Oops!  html.unescape also unescapes plain ampersands...

		xhtml = smartypants.smartypants(xhtml) # Attr.u *should* output unicode characters instead of HTML entities, but it doesn't work

		# Convert entities again
		xhtml = html.unescape(xhtml) # This converts html entites to unicode
		xhtml = regex.sub(r"&([^#a-z])", r"&amp;\1", xhtml) # Oops!  html.unescape also unescapes plain ampersands...

	# Replace sequential em dashes with the two or three em dash character
	xhtml = xhtml.replace("———", "⸻")
	xhtml = xhtml.replace("——", "⸺")

	# Smartypants doesn't do well on em dashes followed by open quotes. Fix that here
	xhtml = regex.sub(r"—”([a-z])", r"—“\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"—’([a-z])", r"—‘\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"-“</p>", r"—”</p>", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"‘”</p>", r"’{}”</p>".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)

	# Remove spaces between en and em dashes
	# Note that we match at least one character before the dashes, so that we don't catch start-of-line em dashes like in poetry.
	xhtml = regex.sub(r"([^\.\s])\s*([–—])\s*", r"\1\2", xhtml)

	# First, remove stray word joiners
	xhtml = xhtml.replace(se.WORD_JOINER, "")

	# Some older texts use the ,— construct; remove that archaichism
	xhtml = xhtml.replace(",—", "—")

	# Fix some common em-dash transcription errors
	xhtml = regex.sub(r"([:;])-([a-z])", r"\1—\2", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([a-z])-“", r"\1—“", xhtml, flags=regex.IGNORECASE)

	# Em dashes and two-em-dashes can be broken before, so add a word joiner between letters/punctuation and the following em dash
	xhtml = regex.sub(r"([^\s{}{}{}])([—⸻])".format(se.WORD_JOINER, se.NO_BREAK_SPACE, se.HAIR_SPACE), r"\1{}\2".format(se.WORD_JOINER), xhtml, flags=regex.IGNORECASE)

	# Add en dashes; don't replace match that is within an html tag, since ids and attrs often containg the pattern DIGIT-DIGIT
	xhtml = regex.sub(r"(?<!<[^>]*)([0-9]+)\-([0-9]+)", r"\1–\2", xhtml)

	# Add a word joiner on both sides of en dashes
	xhtml = regex.sub(r"{}?–{}?".format(se.WORD_JOINER, se.WORD_JOINER), r"{}–{}".format(se.WORD_JOINER, se.WORD_JOINER), xhtml)

	# Add a word joiner if eliding a word with a two-em-dash
	# Word joiner isn't necessary if punctuation follows
	# Note the \p{{P}}.  We must double-curl {} because that's the escape sequence when using .format().  The actual regex should be \p{P} to match punctuation
	xhtml = regex.sub(r"([^\s{}{}{}])⸺".format(se.WORD_JOINER, se.NO_BREAK_SPACE, se.HAIR_SPACE), r"\1{}⸺".format(se.WORD_JOINER), xhtml)
	xhtml = regex.sub(r"⸺([^\s\p{{P}}{}])".format(se.WORD_JOINER), r"⸺{}\1".format(se.WORD_JOINER), xhtml)

	# Remove word joiners from following opening tags--they're usually never correct
	xhtml = regex.sub(r"<([a-z]+)([^>]*?)>{}".format(se.WORD_JOINER), r"<\1\2>", xhtml, flags=regex.IGNORECASE)

	# Finally fix some other mistakes
	xhtml = xhtml.replace("—-", "—")

	# Replace Mr., Mrs., and other abbreviations, and include a non-breaking space
	xhtml = regex.sub(r"\b(Mr|Mr?s|Drs?|Profs?|Lieut|Fr|Lt|Capt|Pvt|Esq|Mt|St|MM|Mmes?|Mlles?)\.?\s+", r"\1.{}".format(se.NO_BREAK_SPACE), xhtml)
	xhtml = regex.sub(r"<abbr>(Mr|Mr?s|Drs?|Profs?|Lieut|Fr|Lt|Capt|Pvt|Esq|Mt|St|MM|Mmes?|Mlles?)\.</abbr>?\s+", r"<abbr>\1.</abbr>{}".format(se.NO_BREAK_SPACE), xhtml)

	xhtml = regex.sub(r"\bNo\.\s+([0-9]+)", r"No.{}\1".format(se.NO_BREAK_SPACE), xhtml)
	xhtml = regex.sub(r"<abbr>No\.</abbr>\s+", r"<abbr>No.</abbr>{}".format(se.NO_BREAK_SPACE), xhtml)

	xhtml = regex.sub(r"([0-9]+)\s<abbr", r"\1{}<abbr".format(se.NO_BREAK_SPACE), xhtml)

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
	xhtml = regex.sub(r"‘([0-9]{2,}[^a-zA-Z0-9’])", r"’\1", xhtml, flags=regex.IGNORECASE)

	xhtml = regex.sub(r"‘([Aa]ve|[Oo]me|[Ii]m|[Mm]idst|[Gg]ainst|[Nn]eath|[Ee]m|[Cc]os|[Tt]is|[Tt]was|[Tt]wixt|[Tt]were|[Tt]would|[Tt]wouldn|[Tt]ween|[Tt]will|[Rr]ound|[Pp]on)\b", r"’\1", xhtml)

	xhtml = regex.sub(r"\b‘e\b", r"’e", xhtml)
	xhtml = regex.sub(r"\b‘([Ee])r\b", r"’\1r", xhtml)
	xhtml = regex.sub(r"\b‘([Ee])re\b", r"’\1re", xhtml)
	xhtml = regex.sub(r"\b‘([Aa])ppen\b", r"’\1ppen", xhtml)
	xhtml = regex.sub(r"\b‘([Aa])ven\b", r"’\1ven", xhtml) #  'aven't

	# nth (as in nth degree)
	xhtml = regex.sub(r"\bn\-?th\b", r"<i>n</i>th", xhtml)

	# Remove double spaces that use se.NO_BREAK_SPACE for spacing
	xhtml = regex.sub(r"{}[{} ]+".format(se.NO_BREAK_SPACE, se.NO_BREAK_SPACE), r" ", xhtml)
	xhtml = regex.sub(r" [{} ]+".format(se.NO_BREAK_SPACE), r" ", xhtml)

	# House style: remove spacing from common Latinisms
	xhtml = regex.sub(r"([Ii])\.\s+e\.", r"\1.e.", xhtml)
	xhtml = regex.sub(r"([Ee])\.\s+g\.", r"\1.g.", xhtml)

	# WARNING! This and below can remove the ending period of a sentence, if AD or BC is the last word!  We need interactive S&R for this
	xhtml = regex.sub(r"([\d\s])A\.\s+D\.", r"\1AD", xhtml)
	xhtml = regex.sub(r"B\.\s+C\.", r"BC", xhtml)

	# Put spacing next to close quotes
	xhtml = regex.sub(r"“[\s{}]*‘".format(se.NO_BREAK_SPACE), r"“{}‘".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"’[\s{}]*”".format(se.NO_BREAK_SPACE), r"’{}”".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"“[\s{}]*’".format(se.NO_BREAK_SPACE), r"“{}’".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"‘[\s{}]*“".format(se.NO_BREAK_SPACE), r"‘{}“".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)

	# We require a non-letter char at the end, otherwise we might match a contraction: “Hello,” ’e said.
	xhtml = regex.sub(r"”[\s{}]*’([^a-zA-Z])".format(se.NO_BREAK_SPACE), r"”{}’\1".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)

	# Fix ellipses spacing
	xhtml = regex.sub(r"\s*\.\s*\.\s*\.\s*", r"…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"[\s{}]?…[\s{}]?\.".format(se.NO_BREAK_SPACE, se.NO_BREAK_SPACE), r".{}…".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"[\s{}]?…[\s{}]?".format(se.NO_BREAK_SPACE, se.NO_BREAK_SPACE), r"{}… ".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"<p([^>]*?)>{}…".format(se.HAIR_SPACE), r"<p\1>…", xhtml, flags=regex.IGNORECASE)

	# Remove spaces between opening tags and ellipses
	xhtml = regex.sub(r"(<[a-z0-9]+[^<]+?>)[\s{}]+?…".format(se.NO_BREAK_SPACE), r"\1…", xhtml, flags=regex.IGNORECASE)

	# Remove spaces between closing tags and ellipses
	xhtml = regex.sub(r"…[\s{}]?(</[a-z0-9]+>)".format(se.NO_BREAK_SPACE), r"…\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"…[\s{}]+([\)”’])".format(se.NO_BREAK_SPACE), r"…\1", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([\(“‘])[\s{}]+…".format(se.NO_BREAK_SPACE), r"\1…", xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"…[\s{}]?([\!\?\.\;\,])".format(se.NO_BREAK_SPACE), r"…{}\1".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([\!\?\.\;”’])[\s{}]?…".format(se.NO_BREAK_SPACE), r"\1{}…".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"\,[\s{}]?…".format(se.NO_BREAK_SPACE), r",{}…".format(se.HAIR_SPACE), xhtml, flags=regex.IGNORECASE)

	# Remove spaces between ellipses and endnotes directly after
	xhtml = regex.sub(r"…[\s{}]?(<a[^>]+?id=\"noteref-[0-9]+\"[^>]*?>)".format(se.NO_BREAK_SPACE), r"…\1", xhtml, flags=regex.IGNORECASE)

	# Don't use . ... if within a clause
	xhtml = regex.sub(r"\.(\s…\s[a-z])", r"\1", xhtml)

	# Remove period from . .. if after punctuation
	xhtml = regex.sub(r"([\!\?\,\;\:]\s*)\.(\s…)", r"\1\2", xhtml)

	# Add non-breaking spaces between amounts with an abbreviated unit.  E.g. 8 oz., 10 lbs.
	xhtml = regex.sub(r"([0-9])\s+([a-z]{1,3}\.)", r"\1{}\2".format(se.NO_BREAK_SPACE), xhtml, flags=regex.IGNORECASE)

	# Add non-breaking spaces between Arabic numbers and AM/PM
	xhtml = regex.sub(r"([0-9])\s+([ap])\.m\.", r"\1{}\2.m.".format(se.NO_BREAK_SPACE), xhtml, flags=regex.IGNORECASE)
	xhtml = regex.sub(r"([0-9])\s+<abbr([^>]*?)>([ap])\.m\.", r"\1{}<abbr\2>\3.m.".format(se.NO_BREAK_SPACE), xhtml, flags=regex.IGNORECASE)

	xhtml = xhtml.replace("Ph.D", "PhD")
	xhtml = regex.sub(r"P\.\s*S\.", r"P.S.", xhtml)

	# Fractions
	xhtml = xhtml.replace("1/4", "¼")
	xhtml = xhtml.replace("1/2", "½")
	xhtml = xhtml.replace("3/4", "¾")
	xhtml = xhtml.replace("1/3", "⅓")
	xhtml = xhtml.replace("2/3", "⅔")
	xhtml = xhtml.replace("1/5", "⅕")
	xhtml = xhtml.replace("2/5", "⅖")
	xhtml = xhtml.replace("3/5", "⅗")
	xhtml = xhtml.replace("4/5", "⅘")
	xhtml = xhtml.replace("1/6", "⅙")
	xhtml = xhtml.replace("5/6", "⅚")
	xhtml = xhtml.replace("1/8", "⅛")
	xhtml = xhtml.replace("3/8", "⅜")
	xhtml = xhtml.replace("5/8", "⅝")
	xhtml = xhtml.replace("7/8", "⅞")

	# Remove spaces between whole numbers and fractions
	xhtml = regex.sub(r"([0-9,]+)\s+([¼½¾⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞])", r"\1\2", xhtml)

	# Use the Unicode Minus glyph (U+2212) for negative numbers
	xhtml = regex.sub(r"([\s>])\-([0-9,]+)", r"\1−\2", xhtml)

	# Convert L to £ if next to a number
	xhtml = regex.sub(r"L([0-9]+)", r"£\1", xhtml)

	# Make sure there are periods after old-style shilling/pence denominations
	xhtml = regex.sub(r"\b([0-9]+)s\.? ([0-9]+)d\.?", r"\1s. \2d.", xhtml)

	# Remove periods after pounds if followed by shillings
	xhtml = regex.sub(r"£([0-9]+)\.? ([0-9]+)s\.?", r"£\1 \2s.", xhtml)

	return xhtml

def hyphenate_file(filename: str, language: str, ignore_h_tags: bool = False) -> None:
	"""
	Add soft hyphens to an XHTML file.

	INPUTS
	filename: A filename containing well-formed XHTML.
	language: An ISO language code, like en-US, or None to auto-detect based on XHTML input
	ignore_h_tags: True to not hyphenate within <h1-6> tags

	OUTPUTS
	None.
	"""

	with open(filename, "r+", encoding="utf-8") as file:
		xhtml = file.read()

		processed_xhtml = se.typography.hyphenate(xhtml, language, ignore_h_tags)

		if processed_xhtml != xhtml:
			file.seek(0)
			file.write(processed_xhtml)
			file.truncate()

def hyphenate(xhtml: str, language: str, ignore_h_tags: bool = False) -> str:
	"""
	Add soft hyphens to a string of XHTML.

	INPUTS
	xhtml: A string of XHTML
	language: An ISO language code, like en-US, or None to auto-detect based on XHTML input
	ignore_h_tags: True to not hyphenate within <h1-6> tags

	OUTPUTS
	A string of XHTML with soft hyphens inserted in words. The output is not guaranteed to be pretty-printed.
	"""

	hyphenators = {}
	soup = BeautifulSoup(xhtml, "lxml")

	if language is None:
		try:
			language = soup.html["xml:lang"]
		except Exception:
			try:
				language = soup.html["lang"]
			except Exception:
				raise se.InvalidLanguageException("No `xml:lang` or `lang` attribute on root <html> element; couldn’t guess file language.")

	try:
		language = language.replace("-", "_")
		if language not in hyphenators:
			hyphenators[language] = Hyphenator(language)
	except Exception:
		raise se.MissingDependencyException("Hyphenator for language \"{}\" not available.\nInstalled hyphenators: {}".format(language, list_installed()))

	text = str(soup.body)
	result = text
	word = ""
	in_tag = False
	tag_name = ""
	reading_tag_name = False
	in_h_tag = False
	pos = 1
	h_opening_tag_pattern = regex.compile("^h[1-6]$")
	h_closing_tag_pattern = regex.compile("^/h[1-6]$")

	# The general idea here is to read the whole contents of the <body> tag character by character.
	# If we hit a <, we ignore the contents until we hit the next >.
	# Otherwise, we consider a word to be an unbroken sequence of alphanumeric characters.
	# We can't just split at whitespace because HTML tags can contain whitespace (attributes for example)
	for char in text:
		process = False

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
		elif not in_tag:
			process = True

		# Do we ignore <h1-6> tags?
		if not reading_tag_name and h_opening_tag_pattern.match(tag_name):
			in_h_tag = True

		if not reading_tag_name and h_closing_tag_pattern.match(tag_name):
			in_h_tag = False

		if ignore_h_tags and in_h_tag:
			process = False

		if process:
			if word != "":
				new_word = word

				# 100 is the hard coded max word length in the hyphenator module
				# Check here to avoid an error
				if len(word) < 100:
					syllables = hyphenators[language].syllables(word)

					if syllables:
						new_word = "\u00AD".join(syllables)

				result = result[:pos - len(word) - 1] + new_word + char + result[pos:]
				pos = pos + len(new_word) - len(word)
			word = ""

		pos = pos + 1

	xhtml = regex.sub(r"<body.+<\/body>", "", xhtml, flags=regex.DOTALL)
	xhtml = xhtml.replace("</head>", "</head>\n\t" + result)

	return xhtml

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

	ldq_pattern = regex.compile(r"\t*<p>(.*?)“")
	lsq_pattern = regex.compile(r"\t*<p>(.*?)‘")

	lsq_count = len([m for m in lsq_pattern.findall(xhtml) if m.count("“") == 0])
	ldq_count = len([m for m in ldq_pattern.findall(xhtml) if m.count("‘") == 0])

	detected_style = "unsure"
	american_percentage = 0

	try:
		american_percentage = (ldq_count / (ldq_count + lsq_count) * 100)
	except ZeroDivisionError:
		pass

	if american_percentage >= threshold:
		detected_style = "american"
	elif 100 - american_percentage >= threshold:
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
	xhtml = regex.sub(r"([a-z])’([a-z])", r"\1<ap>\2", xhtml)
	xhtml = regex.sub(r"(\s+)’([a-z])", r"\1<ap>\2", xhtml)
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
