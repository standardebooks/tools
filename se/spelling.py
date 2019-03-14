#!/usr/bin/env python3
"""
Defines various spelling-related helper functions.
"""

import os
from pkg_resources import resource_filename
import regex
import se


DICTIONARY = []	# Store our hyphenation dictionary so we don't re-read the file on every pass

def modernize_hyphenation(xhtml: str) -> str:
	"""
	Convert old-timey hyphenated compounds into single words based on the passed DICTIONARY.

	INPUTS
	xhtml: A string of XHTML to modernize

	OUTPUTS:
	A string representing the XHTML with its hyphenation modernized
	"""

	# First, initialize our dictionary if we haven't already
	if not se.spelling.DICTIONARY:
		se.spelling.DICTIONARY = set(line.strip().lower() for line in open(resource_filename("se", os.path.join("data", "words"))))

	# Easy fix for a common case
	xhtml = regex.sub(r"\b([Nn])ow-a-days\b", r"\1owadays", xhtml)	# now-a-days -> nowadays

	result = regex.findall(r"\b[^\W\d_]+\-[^\W\d_]+\b", xhtml)

	for word in set(result): # set() removes duplicates
		new_word = word.replace("-", "").lower()
		if new_word in se.spelling.DICTIONARY:
			# To preserve capitalization of the first word, we get the individual parts
			# then replace the original match with them joined together and titlecased.
			lhs = regex.sub(r"\-.+$", r"", word)
			rhs = regex.sub(r"^.+?\-", r"", word)
			xhtml = regex.sub(r"" + lhs + "-" + rhs, lhs + rhs.lower(), xhtml)

	# Quick fix for a common error cases
	xhtml = xhtml.replace("z3998:nonfiction", "z3998:non-fiction")
	xhtml = regex.sub(r"\b([Dd])og’seared", r"\1og’s-eared", xhtml)
	xhtml = regex.sub(r"\b([Mm])anat-arms", r"\1an-at-arms", xhtml)
	xhtml = regex.sub(r"\b([Tt])abled’hôte", r"\1able-d’hôte", xhtml)

	return xhtml

def modernize_spelling(xhtml: str) -> str:
	"""
	Convert old-timey spelling on a case-by-case basis.

	INPUTS
	xhtml: A string of XHTML to modernize
	language: The IETF language tag of the XHTML, like "en-US" or "en-GB"

	OUTPUTS:
	A string representing the XHTML with its spelling modernized
	"""

	# What language are we using?
	language = regex.search(r"<html[^>]+?xml:lang=\"([^\"]+)\"", xhtml)
	if language is None or (language.group(1) != "en-US" and language.group(1) != "en-GB"):
		raise se.InvalidLanguageException("No valid xml:lang attribute in <html> root. Only en-US and en-GB are supported.")

	# ADDING NEW WORDS TO THIS LIST:
	# A good way to check if a word is "archaic" is to do a Google N-Gram search: https://books.google.com/ngrams/graph?case_insensitive=on&year_start=1800&year_end=2000&smoothing=3
	# Remember that en-US and en-GB differ significantly, and just because a word might seem strange to you, doesn't mean it's not the common case in the other variant.
	# If Google N-Gram shows that a word has declined significantly in usage in BOTH en-US and en-GB (or the SE editor-in-chief makes an exception) then it may be a good candidate to add to this list.

	xhtml = regex.sub(r"\b([Dd])evelope\b", r"\1evelop", xhtml)			# develope -> develop
	xhtml = regex.sub(r"\b([Oo])ker\b", r"\1cher", xhtml)				# oker -> ocher
	xhtml = regex.sub(r"\b([Ww])ellnigh\b", r"\1ell-nigh", xhtml)			# wellnigh -> well-nigh
	xhtml = regex.sub(r"\b([Tt]he|[Aa]nd|[Oo]r) what not(?! to)\b", r"\1 whatnot", xhtml)	# what not -> whatnot
	xhtml = regex.sub(r"\b([Gg])ood\-bye?\b", r"\1oodbye", xhtml)			# good-by -> goodbye
	xhtml = regex.sub(r"\b([Hh])ind(u|oo)stanee", r"\1industani", xhtml)		# hindoostanee -> hindustani
	xhtml = regex.sub(r"\b([Hh])indoo", r"\1indu", xhtml)				# hindoo -> hindu
	xhtml = regex.sub(r"\b([Ee])xpence", r"\1xpense", xhtml)			# expence -> expense
	xhtml = regex.sub(r"\b([Ll])otos", r"\1otus", xhtml)				# lotos -> lotus
	xhtml = regex.sub(r"\b([Ss])collop", r"\1callop", xhtml)			# scollop -> scallop
	xhtml = regex.sub(r"\b([Ss])ubtil(?!(ize|izing))", r"\1ubtle", xhtml)		# subtil -> subtle (but "subtilize" and "subtilizing")
	xhtml = regex.sub(r"\bQuoiff", r"Coif", xhtml)					# quoiff -> coif
	xhtml = regex.sub(r"\bquoiff", r"coif", xhtml)					# quoiff -> coif
	xhtml = regex.sub(r"\bIndorse", r"Endorse", xhtml)				# indorse -> endorse
	xhtml = regex.sub(r"\bindorse", r"endorse", xhtml)				# indorse -> endorse
	xhtml = regex.sub(r"\bIntrust", r"Entrust", xhtml)				# Intrust -> Entrust
	xhtml = regex.sub(r"\bintrust", r"entrust", xhtml)				# intrust -> entrust
	xhtml = regex.sub(r"\bPhantas(y|ie)", r"Fantasy", xhtml)			# phantasie -> fantasy
	xhtml = regex.sub(r"\bphantas(y|ie)", r"fantasy", xhtml)			# phantasie -> fantasy
	xhtml = regex.sub(r"\bPhantastic", r"Fantastic", xhtml)				# phantastic -> fantastic
	xhtml = regex.sub(r"\bphantastic", r"fantastic", xhtml)				# phantastic -> fantastic
	xhtml = regex.sub(r"\bPhrensy", r"Frenzy", xhtml)				# Phrensy -> Frenzy
	xhtml = regex.sub(r"\bphrensy", r"frenzy", xhtml)				# phrensy -> frenzy
	xhtml = regex.sub(r"\b([Mm])enage\b", r"\1énage", xhtml)			# menage -> ménage
	xhtml = regex.sub(r"([Hh])ypothenuse", r"\1ypotenuse", xhtml)			# hypothenuse -> hypotenuse
	xhtml = regex.sub(r"[‘’]([Bb])us\b", r"\1us", xhtml)				# ’bus -> bus
	xhtml = regex.sub(r"([Nn])aïve", r"\1aive", xhtml)				# naïve -> naive
	xhtml = regex.sub(r"([Nn])a[ïi]vet[ée]", r"\1aivete", xhtml)			# naïveté -> naivete
	xhtml = regex.sub(r"&amp;c\.", r"etc.", xhtml)					# &c. -> etc.
	xhtml = regex.sub(r"([Pp])rot[ée]g[ée]", r"\1rotégé", xhtml)			# protege -> protégé
	xhtml = regex.sub(r"([Tt])ete-a-tete", r"\1ête-à-tête", xhtml)			# tete-a-tete -> tête-à-tête
	xhtml = regex.sub(r"([Vv])is-a-vis", r"\1is-à-vis", xhtml)			# vis-a-vis _> vis-à-vis
	xhtml = regex.sub(r"([Ff])acade", r"\1açade", xhtml)				# facade -> façade
	xhtml = regex.sub(r"([Cc])h?ateau(s?\b)", r"\1hâteau\2", xhtml)			# chateau -> château
	xhtml = regex.sub(r"([Hh])abitue", r"\1abitué", xhtml)				# habitue -> habitué
	xhtml = regex.sub(r"\b([Bb])lase\b", r"\1lasé", xhtml)				# blase -> blasé
	xhtml = regex.sub(r"\b([Bb])bee[’']s[ \-]wax\b", r"\1eeswax", xhtml)		# bee’s-wax -> beeswax
	xhtml = regex.sub(r"\b([Cc])afe\b", r"\1afé", xhtml)				# cafe -> café
	xhtml = regex.sub(r"\b([Cc])afes\b", r"\1afés", xhtml)				# cafes -> cafés; We break up cafe so that we don't catch 'cafeteria'
	xhtml = regex.sub(r"([Mm])êlée", r"\1elee", xhtml)				# mêlée -> melee
	xhtml = regex.sub(r"\b([Ff])ete([sd])?\b", r"\1ête\2", xhtml)			# fete -> fête
	xhtml = regex.sub(r"\b([Rr])ôle\b", r"\1ole", xhtml)				# rôle -> role
	xhtml = regex.sub(r"\b([Cc])oö", r"\1oo", xhtml)				# coö -> coo (as in coöperate)
	xhtml = regex.sub(r"\b([Rr])eë", r"\1ee", xhtml)				# reë -> ree (as in reëvaluate)
	xhtml = regex.sub(r"\b([Dd])aïs\b", r"\1ais", xhtml)				# daïs -> dais
	xhtml = regex.sub(r"\b([Cc])oup\-de\-grace", r"\1oup-de-grâce", xhtml)		# coup-de-grace -> coup-de-grâce
	xhtml = regex.sub(r"\b([Cc])anape", r"\1anapé", xhtml)				# canape -> canapé
	xhtml = regex.sub(r"\b([Pp])recis\b", r"\1récis", xhtml)			# precis -> précis
	xhtml = regex.sub(r"\b([Gg])ood\-by([^e])", r"\1oodbye\2", xhtml)		# good-by -> goodbye
	xhtml = regex.sub(r"\b([Gg])ood\-night", r"\1ood night", xhtml)			# good-night -> good night
	xhtml = regex.sub(r"\b([Gg])ood\-morning", r"\1ood morning", xhtml)		# good-morning -> good morning
	xhtml = regex.sub(r"\b([Gg])ood\-evening", r"\1ood evening", xhtml)		# good-evening -> good evening
	xhtml = regex.sub(r"\b([Gg])ood\-day", r"\1ood day", xhtml)			# good-day -> good day
	xhtml = regex.sub(r"\b([Gg])ood\-afternoon", r"\1ood afternoon", xhtml)		# good-afternoon -> good afternoon
	xhtml = regex.sub(r"\b([Bb])ete noir", r"\1ête noir", xhtml)			# bete noir -> bête noir
	xhtml = regex.sub(r"\bEclat\b", r"Éclat", xhtml)				# eclat -> éclat
	xhtml = regex.sub(r"\beclat\b", r"éclat", xhtml)				# eclat -> éclat
	xhtml = regex.sub(r"\ba la\b", r"à la", xhtml)					# a la -> à la
	xhtml = regex.sub(r"\ba propos\b", r"apropos", xhtml)				# a propos -> apropos
	xhtml = regex.sub(r"\bper cent(s?)\b", r"percent\1", xhtml)			# per cent -> percent
	xhtml = regex.sub(r"\bpercent\.(\s+[a-z])", r"percent\1", xhtml)		# percent. followed by lowercase -> percent
	xhtml = regex.sub(r"\bpercent\.,\b", r"percent,", xhtml)			# per cent. -> percent
	xhtml = regex.sub(r"\b([Ff])iance", r"\1iancé", xhtml)				# fiance -> fiancé
	xhtml = regex.sub(r"\b([Oo])utre\b", r"\1utré", xhtml)				# outre -> outré
	xhtml = regex.sub(r"\b([Ff])etich", r"\1etish", xhtml)				# fetich -> fetish
	xhtml = regex.sub(r"\b([Pp])igstye\b", r"\1igsty", xhtml)			# pigstye -> pigsty
	xhtml = regex.sub(r"\b([Pp])igstyes\b", r"\1igsties", xhtml)			# pigstyes -> pigsties
	xhtml = regex.sub(r"\b([Cc])lew(s?)\b", r"\1lue\2", xhtml)			# clew -> clue
	xhtml = regex.sub(r"\b[ÀA]\s?propos\b", r"Apropos", xhtml)			# à propos -> apropos
	xhtml = regex.sub(r"\b[àa]\s?propos\b", r"apropos", xhtml)			# à propos -> apropos
	xhtml = regex.sub(r"\b([Nn])ew comer(s?)\b", r"\1ewcomer\2", xhtml)		# new comer -> newcomer
	xhtml = regex.sub(r"\b([Pp])ease\b(?![ \-]pudding)", r"\1eas", xhtml)		# pease -> peas (but "pease pudding")
	xhtml = regex.sub(r"\b([Ss])uch like\b", r"\1uchlike", xhtml)			# such like -> suchlike
	xhtml = regex.sub(r"\b([Ee])mployé", r"\1mployee", xhtml)			# employé -> employee
	xhtml = regex.sub(r"\b(?<!ancien )([Rr])égime", r"\1egime", xhtml)		# régime -> regime (but "ancien régime")
	xhtml = regex.sub(r"\b([Bb])urthen", r"\1urden", xhtml)				# burthen -> burden
	xhtml = regex.sub(r"\b([Dd])isburthen", r"\1isburden", xhtml)			# disburthen -> disburthen
	xhtml = regex.sub(r"\b[EÉ]lys[eé]e", r"Élysée", xhtml)				# Elysee -> Élysée
	xhtml = regex.sub(r"\b([Ll])aw suit", r"\1awsuit", xhtml)			# law suit -> lawsuit
	xhtml = regex.sub(r"\bIncase", r"Encase", xhtml)				# incase -> encase
	xhtml = regex.sub(r"\bincase", r"encase", xhtml)				# incase -> encase
	xhtml = regex.sub(r"\b([Cc])ocoa-?nut", r"\1oconut", xhtml)			# cocoanut / cocoa-nut -> coconut
	xhtml = regex.sub(r"\b([Ww])aggon", r"\1agon", xhtml)				# waggon -> wagon
	xhtml = regex.sub(r"\b([Ss])wop", r"\1wap", xhtml)				# swop -> swap
	xhtml = regex.sub(r"\b([Ll])acquey", r"\1ackey", xhtml)				# lacquey -> lackey
	xhtml = regex.sub(r"\b([Bb])ric-à-brac", r"\1ric-a-brac", xhtml)		# bric-à-brac -> bric-a-brac
	xhtml = regex.sub(r"\b([Kk])iosque", r"\1iosk", xhtml)				# kiosque -> kiosk
	xhtml = regex.sub(r"\b([Dd])epôt", r"\1epot", xhtml)				# depôt -> depot
	xhtml = regex.sub(r"(?<!compl)exion", r"ection", xhtml)				# -extion -> -exction (connexion, reflexion, etc., but "complexion")
	xhtml = regex.sub(r"\b([Dd])ulness", r"\1ullness", xhtml)			# dulness -> dullness
	xhtml = regex.sub(r"\b([Ff])iord", r"\1jord", xhtml)				# fiord -> fjord
	xhtml = regex.sub(r"\b([Ff])ulness\b", r"\1ullness", xhtml)			# fulness -> fullness (but not for ex. thoughtfulness)
	xhtml = regex.sub(r"\b’([Pp])hone", r"\1hone", xhtml)				# ’phone -> phone
	xhtml = regex.sub(r"\b([Ss])hew", r"\1how", xhtml)				# shew -> show
	xhtml = regex.sub(r"\b([Tt])rowsers", r"\1rousers", xhtml)			# trowsers -> trousers
	xhtml = regex.sub(r"\b([Bb])iass", r"\1ias", xhtml)				# biass -> bias
	xhtml = regex.sub(r"\b([Cc])huse", r"\1hoose", xhtml)				# chuse -> choose
	xhtml = regex.sub(r"\b([Cc])husing", r"\1hoosing", xhtml)			# chusing -> choosing
	xhtml = regex.sub(r"\b([Cc])ontroul(s?)\b", r"\1ontrol\2", xhtml)	# controul -> control
	xhtml = regex.sub(r"\b([Cc])ontroul(ing|ed)", r"\1ontroll\2", xhtml)	# controuling/ed -> controlling/ed
	xhtml = regex.sub(r"\b([Ss])urpriz(e|ing)", r"\1urpris\2", xhtml)		# surprize->surprise, surprizing->surprising
	xhtml = regex.sub(r"\b([Dd])oat\b", r"\1ote", xhtml)				# doat -> dote
	xhtml = regex.sub(r"\b([Dd])oat(ed|ing)", r"\1ot\2", xhtml)			# doating -> doting
	xhtml = regex.sub(r"\b([Ss])topt", r"\1topped", xhtml)				# stopt -> stopped
	xhtml = regex.sub(r"\b([Ss])tept", r"\1tepped", xhtml)				# stept -> stepped
	xhtml = regex.sub(r"\b([Ss])ecresy", r"\1ecrecy", xhtml)			# secresy -> secrecy
	xhtml = regex.sub(r"\b([Mm])esalliance", r"\1ésalliance", xhtml)		# mesalliance -> mésalliance
	xhtml = regex.sub(r"\b([Ss])ate\b", r"\1at", xhtml)				# sate -> sat
	xhtml = regex.sub(r"\b([Aa])ttache\b", r"\1ttaché", xhtml)			# attache -> attaché
	xhtml = regex.sub(r"\b([Pp])orte[\- ]coch[eè]re\b", r"\1orte-cochère", xhtml)	# porte-cochere -> porte-cochère
	xhtml = regex.sub(r"\b([Nn])égligée?(s?)\b", r"\1egligee\2", xhtml)		# négligée -> negligee
	xhtml = regex.sub(r"\b([Ss])hort cut(s?)\b", r"\1hortcut\2", xhtml)		# short cut -> shortcut
	xhtml = regex.sub(r"\b([Ff])ocuss", r"\1ocus", xhtml)				# focuss -> focus
	xhtml = regex.sub(r"\b([Mm])ise[ \-]en[ \-]sc[eè]ne", r"\1ise-en-scène", xhtml)	# mise en scene -> mise-en-scène
	xhtml = regex.sub(r"\b([Nn])ee\b", r"\1ée", xhtml)				# nee -> née
	xhtml = regex.sub(r"\b([Ee])au[ \-]de[ \-]Cologne\b", r"\1au de cologne", xhtml)	# eau de Cologne -> eau de cologne
	xhtml = regex.sub(r"\b([Ss])enor", r"\1eñor", xhtml)				# senor -> señor (senores, senorita/s, etc.)
	xhtml = regex.sub(r"\b([Gg])ramme?(s)?\b", r"\1ram\2", xhtml)			# gramm/grammes -> gram/grams
	xhtml = regex.sub(r"\b([Aa])larum\b", r"\1larm", xhtml)				# alarum -> alarm
	xhtml = regex.sub(r"\b([Bb])owlder(s?)\b", r"\1oulder\2", xhtml)		# bowlder/bowlders -> boulder/boulders
	xhtml = regex.sub(r"\b([Dd])istingue\b", r"\1istingué", xhtml)			# distingue -> distingué
	xhtml = regex.sub(r"\b[EÉ]cart[eé]\b", r"Écarté", xhtml)			# ecarte -> écarté
	xhtml = regex.sub(r"\b[eé]cart[eé]\b", r"écarté", xhtml)			# ecarte -> écarté
	xhtml = regex.sub(r"\b([Pp])ere\b", r"\1ère", xhtml)				# pere -> père (e.g. père la chaise)
	xhtml = regex.sub(r"\b([Tt])able(s?) d’hote\b", r"\1able\2 d’hôte", xhtml)	# table d'hote -> table d'hôte
	xhtml = regex.sub(r"\b([Ee])au(x?)[ \-]de[ \-]vie\b", r"\1au\2-de-vie", xhtml)	# eau de vie -> eau-de-vie
	xhtml = regex.sub(r"\b3d\b", r"3rd", xhtml)						# 3d -> 3rd (warning: check that we don't convert 3d in the "3 pence" sense!)
	xhtml = regex.sub(r"\b2d\b", r"2nd", xhtml)						# 2d -> 2nd (warning: check that we don't convert 2d in the "2 pence" sense!)
	xhtml = regex.sub(r"\b([Mm])ia[uo]w", r"\1eow", xhtml)				# miauw, miaow -> meow
	xhtml = regex.sub(r"\b([Cc])aviare", r"\1aviar", xhtml)				# caviare -> caviar
	xhtml = regex.sub(r"\b([Ss])ha’n’t", r"\1han’t", xhtml)				# sha'n't -> shan't (see https://english.stackexchange.com/questions/71414/apostrophes-in-contractions-shant-shant-or-shant)
	xhtml = regex.sub(r"\b([Ss])[uû]ret[eé]", r"\1ûreté", xhtml)			# Surete -> Sûreté
	xhtml = regex.sub(r"\b([Ss])eance", r"\1éance", xhtml)				# seance -> séance

	# Normalize some names
	xhtml = regex.sub(r"Moliere", r"Molière", xhtml)				# Moliere -> Molière
	xhtml = regex.sub(r"Tolstoi", r"Tolstoy", xhtml)				# Tolstoi -> Tolstoy
	xhtml = regex.sub(r"Buonaparte", r"Bonaparte", xhtml)				# Buonaparte -> Bonaparte
	xhtml = regex.sub(r"Shake?spear([^ie])", r"Shakespeare\1", xhtml)		# Shakespear/Shakspear -> Shakespeare
	xhtml = regex.sub(r"Raffaelle", r"Raphael", xhtml)				# Raffaelle -> Raphael
	xhtml = regex.sub(r"Michael Angelo", r"Michaelangelo", xhtml)			# Michael Angelo -> Michaelangelo
	xhtml = regex.sub(r"\bVergil", r"Virgil", xhtml)				# Vergil -> Virgil
	xhtml = regex.sub(r"\bVishnoo", r"Vishnu", xhtml)				# Vishnoo -> Vishnu
	xhtml = regex.sub(r"\bPekin\b", r"Peking", xhtml)				# Pekin -> Peking
	xhtml = regex.sub(r"\bBuenos Ayres\b", r"Buenos Aires", xhtml)			# Buenos Ayres -> Buenos Aires
	xhtml = regex.sub(r"\bCracow", r"Krakow", xhtml)				# Cracow -> Krakow
	xhtml = regex.sub(r"\bKief", r"Kiev", xhtml)					# Kief -> Kiev
	xhtml = regex.sub(r"\bRoumanian", r"Romanian", xhtml)				# Roumanian -> Romanian

	# Remove archaic diphthongs
	xhtml = regex.sub(r"\b([Mm])edi(æ|ae)val", r"\1edieval", xhtml)
	xhtml = xhtml.replace("Cæsar", "Caesar")
	xhtml = xhtml.replace("Crœsus", "Croesus")
	xhtml = xhtml.replace("\bæon\b", "aeon")
	xhtml = xhtml.replace("\bÆon\b", "Aeon")
	xhtml = xhtml.replace("Æschylus", "Aeschylus")
	xhtml = xhtml.replace("æsthet", "aesthet") # aesthetic, aesthete, etc.
	xhtml = xhtml.replace("Æsthet", "Aesthet") # aesthetic, aesthete, etc.
	xhtml = regex.sub(r"\b([Hh])yæna", r"\1yena", xhtml)
	xhtml = xhtml.replace("Œdip", "Oedip") # Oedipus, Oedipal
	xhtml = regex.sub(r"\b([Pp])æan", r"\1aean", xhtml)
	xhtml = regex.sub(r"\b([Vv])ertebræ", r"\1ertebrae", xhtml)

	if language == "en-US":
		xhtml = regex.sub(r"\b([Cc])osey", r"\1ozy", xhtml)
		xhtml = regex.sub(r"\b([Mm])anœuve?r", r"\1aneuver", xhtml) # Omit last letter to catch both maneuverS and maneuverING

	if language == "en-GB":
		xhtml = regex.sub(r"\b([Cc])osey", r"\1osy", xhtml)
		xhtml = regex.sub(r"\b([Mm])anœuve?r", r"\1anoeuvr", xhtml) # Omit last letter to catch both maneuverS and maneuverING

	return xhtml
