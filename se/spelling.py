#!/usr/bin/env python3
"""
Defines various spelling-related helper functions.
"""

from typing import Set
import importlib_resources
import regex
import se

DICTIONARY: Set[str] = set()	# Store our hyphenation dictionary so we don't re-read the file on every pass

def get_xhtml_language(xhtml: str) -> str:
	"""
	Try to get the IETF lang tag for a complete XHTML document
	"""

	supported_languages = ["en-US", "en-GB", "en-AU", "en-CA", "en-IE"]

	match = regex.search(r"<html[^>]+?xml:lang=\"([^\"]+)\"", xhtml)

	if match:
		language = match.group(1)
	else:
		language = None

	if language not in supported_languages:
		raise se.InvalidLanguageException(f"No valid [attr]xml:lang[/] attribute in [xhtml]<html>[/] element. Only [text]{'[/], [text]'.join(supported_languages[:-1])}[/], and [text]{supported_languages[-1]}[/] are supported.")

	return language

def modernize_hyphenation(xhtml: str) -> str:
	"""
	Convert old-timey hyphenated compounds into single words based on the passed DICTIONARY.

	INPUTS
	xhtml: A string of XHTML to modernize

	OUTPUTS
	A string representing the XHTML with its hyphenation modernized
	"""

	# First, initialize our dictionary if we haven't already
	if not se.spelling.DICTIONARY:
		with importlib_resources.open_text("se.data", "words") as dictionary:
			se.spelling.DICTIONARY = {line.strip().lower() for line in dictionary}

	# Easy fix for a common case
	xhtml = regex.sub(r"\b([Nn])ow-a-days\b", r"\1owadays", xhtml)	# now-a-days -> nowadays

	# The non-capturing group at the beginning tries to prevent
	# bad matches like stag's-horn -> stag'shorn or dog's-eared -> dog'seared
	result = regex.findall(r"(?<![’\'])\b[^\W\d_]+\-[^\W\d_]+\b", xhtml)

	for word in set(result): # set() removes duplicates
		new_word = word.replace("-", "").lower()
		if new_word in se.spelling.DICTIONARY:
			# To preserve capitalization of the first word, we get the individual parts
			# then replace the original match with them joined together and titlecased.
			lhs = regex.sub(r"\-.+$", r"", word)
			rhs = regex.sub(r"^.+?\-", r"", word)
			xhtml = regex.sub(fr"{lhs}-{rhs}", lhs + rhs.lower(), xhtml)

	# Quick fix for a common error cases
	xhtml = xhtml.replace("z3998:nonfiction", "z3998:non-fiction")
	xhtml = regex.sub(r"\b([Mm])anat-arms", r"\1an-at-arms", xhtml)
	xhtml = regex.sub(r"\b([Tt])abled’hôte", r"\1able-d’hôte", xhtml)
	xhtml = regex.sub(r"\b([Pp])ita-pat", r"\1it-a-pat", xhtml)

	return xhtml

def detect_problem_spellings(xhtml: str) -> list:
	"""
	Return a list of potential problem spellings, that cannot be scripted due to a
	word having various meanings.

	For example, "staid" can be an archaic spelling of "stayed",
	or as an adjective it could mean "marked by settled sedateness
	and often prim self-restraint".

	INPUTS
	xhtml: A string of XHTML to inspect

	OUTPUTS
	A list of strings representing potential words to manually inspect
	"""

	# Uncomment if we eventually need the document language
	# language = get_xhtml_language(xhtml)
	output = []

	if regex.search(r"\bstaid\b", xhtml):
		output.append("“staid” detected. This should be modernized if it is the past tense of “stay,” but not if used as an adjective meaning “sedate or prim.”")

	if regex.search(r"\bcozen\b", xhtml):
		output.append("“cozen” detected. This should be modernized if it means “cousin,” but not if used to mean “to deceive or win over.”")

	if regex.search(r"\bgrown-?up\b", xhtml):
		output.append("“grownup” or “grown-up” detected. Confirm that “grownup” is strictly a noun, and “grown-up” is strictly an adjective.")

	if regex.search(r"\bcommon[\-\s]?sense\b", xhtml):
		output.append("“commonsense” or “common sense” or “common-sense” detected. Confirm that “common sense” and “common-sense” are strictly nouns, and that “commonsense” is strictly an adjective.")

	if regex.search(r"\bmann?ikin\b", xhtml):
		output.append("“mannikin” or “manikin” detected. Confirm that “mannikin” is used in the sense of a small person, and “mannequin” is used in the sense of a dummy or figure.")

	if regex.search(r"\bgripe", xhtml):
		output.append("“gripe” or “griped” detected. Confirm that “gripe” is used in the sense of illness or complaint, not in the sense of “grip” or “gripped.”")

	if regex.search(r"\bmay[\-\s]?day", xhtml):
		output.append("“mayday” or “may day” or “may-day” detected. Confirm that “may day” and “may-day” refer to the day, and that “mayday” is used in the sense of a distress signal.")

	if regex.search(r"\bfree[\-\s]?will", xhtml):
		output.append("“freewill” or “free will” or “free-will” detected. Confirm that “free will” and “free-will” are strictly nouns, and that “freewill” is strictly an adjective.")

	return output

def modernize_spelling(xhtml: str) -> str:
	"""
	Convert old-timey spelling on a case-by-case basis.

	INPUTS
	xhtml: A string of XHTML to modernize

	OUTPUTS
	A string representing the XHTML with its spelling modernized
	"""

	language = get_xhtml_language(xhtml)

	# ADDING NEW WORDS TO THIS LIST:
	# A good way to check if a word is "archaic" is to do a Google N-Gram search: https://books.google.com/ngrams/graph?case_insensitive=on&year_start=1800&year_end=2000&smoothing=3
	# Remember that en-US and en-GB differ significantly, and just because a word might seem strange to you, doesn't mean it's not the common case in the other variant.
	# If Google N-Gram shows that a word has declined significantly in usage in BOTH en-US and en-GB (or the SE editor-in-chief makes an exception) then it may be a good candidate to add to this list.

	xhtml = regex.sub(r"\b([Dd])evelope\b", r"\1evelop", xhtml)			# develope -> develop
	xhtml = regex.sub(r"\b([Oo])ker\b", r"\1cher", xhtml)				# oker -> ocher
	xhtml = regex.sub(r"\b([Ww])ellnigh\b", r"\1ell-nigh", xhtml)			# wellnigh -> well-nigh
	xhtml = regex.sub(r"\b([Tt]he|[Aa]nd|[Oo]r) what not(?! to)\b", r"\1 whatnot", xhtml)	# what not -> whatnot
	xhtml = regex.sub(r"\b([Gg])ood[\-]?bye?\b", r"\1oodbye", xhtml)		# good-by -> goodbye
	xhtml = regex.sub(r"\b([Gg])ood\sbye\b", r"\1oodbye", xhtml)			# good bye -> goodbye (Note that we can't do `good by` -> `goodby` because one might do good by someone.
	xhtml = regex.sub(r"\b([Gg])ood[\-\s]?bye?s\b", r"\1oodbyes", xhtml)		# good bys -> goodbyes
	xhtml = regex.sub(r"\b([Hh])ind(u|oo)stanee", r"\1industani", xhtml)		# hindoostanee -> hindustani
	xhtml = regex.sub(r"\b([Hh])indoo", r"\1indu", xhtml)				# hindoo -> hindu
	xhtml = regex.sub(r"\b([Ee])xpence", r"\1xpense", xhtml)			# expence -> expense
	xhtml = regex.sub(r"\b([Ll])otos", r"\1otus", xhtml)				# lotos -> lotus
	xhtml = regex.sub(r"\b([Ss])collop", r"\1callop", xhtml)			# scollop -> scallop
	xhtml = regex.sub(r"\b([Ss])ubtile?(?!(ize|izing))", r"\1ubtle", xhtml)		# subtil -> subtle (but "subtilize" and "subtilizing")
	xhtml = regex.sub(r"\bQuoiff", r"Coif", xhtml)					# quoiff -> coif
	xhtml = regex.sub(r"\bquoiff", r"coif", xhtml)					# quoiff -> coif
	xhtml = regex.sub(r"\bIndorse", r"Endorse", xhtml)				# Indorse -> Endorse
	xhtml = regex.sub(r"\bindorse", r"endorse", xhtml)				# indorse -> endorse
	xhtml = regex.sub(r"\bIntrust", r"Entrust", xhtml)				# Intrust -> Entrust
	xhtml = regex.sub(r"\bintrust", r"entrust", xhtml)				# intrust -> entrust
	xhtml = regex.sub(r"\bPhantasies", r"Fantasies", xhtml)				# Phantasies -> Fantasies
	xhtml = regex.sub(r"\bphantasies", r"fantasies", xhtml)				# phantasies -> fantasies
	xhtml = regex.sub(r"\bPhantas(y|ie)", r"Fantasy", xhtml)			# Phantasie -> Fantasy
	xhtml = regex.sub(r"\bphantas(y|ie)", r"fantasy", xhtml)			# phantasie -> fantasy
	xhtml = regex.sub(r"\bPhantastic", r"Fantastic", xhtml)				# Phantastic -> Fantastic
	xhtml = regex.sub(r"\bphantastic", r"fantastic", xhtml)				# phantastic -> fantastic
	xhtml = regex.sub(r"\bPhren[sz](y|ie)", r"Frenz\1", xhtml)			# Phrensy/phrensied -> Frenzy
	xhtml = regex.sub(r"\bphren[sz](y|ie)", r"frenz\1", xhtml)			# phrensy/phrensied -> frenzy
	xhtml = regex.sub(r"\b([Mm])enage\b", r"\1énage", xhtml)			# menage -> ménage
	xhtml = regex.sub(r"([Hh])ypothenuse", r"\1ypotenuse", xhtml)			# hypothenuse -> hypotenuse
	xhtml = regex.sub(r"[‘’]([Bb])us\b", r"\1us", xhtml)				# ’bus -> bus
	xhtml = regex.sub(r"([Nn])aïve", r"\1aive", xhtml)				# naïve -> naive
	xhtml = regex.sub(r"([Nn])a[ïi]vet[ée]", r"\1aivete", xhtml)			# naïveté -> naivete
	xhtml = regex.sub(r"&amp;c\.", r"etc.", xhtml)					# &c. -> etc.
	xhtml = regex.sub(r"([Pp])rot[ée]g[ée]", r"\1rotégé", xhtml)			# protege -> protégé
	xhtml = regex.sub(r"([Tt])ete-a-tete", r"\1ête-à-tête", xhtml)			# tete-a-tete -> tête-à-tête
	xhtml = regex.sub(r"([Vv])is-a-vis", r"\1is-à-vis", xhtml)			# vis-a-vis -> vis-à-vis
	xhtml = regex.sub(r"([Ff])acade", r"\1açade", xhtml)				# facade -> façade
	xhtml = regex.sub(r"([Cc])h?ateau([sx]?\b)", r"\1hâteau\2", xhtml)		# chateau -> château
	xhtml = regex.sub(r"([Hh])abitue", r"\1abitué", xhtml)				# habitue -> habitué
	xhtml = regex.sub(r"\b([Bb])lase\b", r"\1lasé", xhtml)				# blase -> blasé
	xhtml = regex.sub(r"\b([Bb])bee[’']s[ \-]wax\b", r"\1eeswax", xhtml)		# bee’s-wax -> beeswax
	xhtml = regex.sub(r"\b([Cc])afe\b", r"\1afé", xhtml)				# cafe -> café
	xhtml = regex.sub(r"\b([Cc])afes\b", r"\1afés", xhtml)				# cafes -> cafés; We break up cafe so that we don't catch 'cafeteria'
	xhtml = regex.sub(r"([Mm])êlée", r"\1elee", xhtml)				# mêlée -> melee
	xhtml = regex.sub(r"\b([Ff])ete([sd])?\b", r"\1ête\2", xhtml)			# fete -> fête
	xhtml = regex.sub(r"\b([Rr])ôle(s?)\b", r"\1ole\2", xhtml)			# rôle -> role
	xhtml = regex.sub(r"\b([Cc])oö", r"\1oo", xhtml)				# coö -> coo (as in coöperate)
	xhtml = regex.sub(r"\b([Rr])eë", r"\1ee", xhtml)				# reë -> ree (as in reëvaluate)
	xhtml = regex.sub(r"\b([Pp])reë", r"\1ree", xhtml)				# preë -> pree (as in preëmpt)
	xhtml = regex.sub(r"\b([Cc])oërc", r"\1oerc", xhtml)				# coërc -> coerc (as in coërcion)
	xhtml = regex.sub(r"\b([Cc])oëd", r"\1oed", xhtml)				# coëd -> coed (as in coëducation)
	xhtml = regex.sub(r"\b([Dd])aïs\b", r"\1ais", xhtml)				# daïs -> dais
	xhtml = regex.sub(r"\b([Cc])oup[\- ]de[\- ]gr[aâ]ce", r"\1oup de grâce", xhtml)	# coup-de-grace -> coup-de-grâce
	xhtml = regex.sub(r"\b([Cc])anape", r"\1anapé", xhtml)				# canape -> canapé
	xhtml = regex.sub(r"\b([Pp])recis\b", r"\1récis", xhtml)			# precis -> précis
	xhtml = regex.sub(r"\b([Gg])ood\-night", r"\1ood night", xhtml)			# good-night -> good night
	xhtml = regex.sub(r"\b([Gg])ood\-morning", r"\1ood morning", xhtml)		# good-morning -> good morning
	xhtml = regex.sub(r"\b([Gg])ood\-evening", r"\1ood evening", xhtml)		# good-evening -> good evening
	xhtml = regex.sub(r"\b([Gg])ood\-day", r"\1ood day", xhtml)			# good-day -> good day
	xhtml = regex.sub(r"\b([Gg])ood\-afternoon", r"\1ood afternoon", xhtml)		# good-afternoon -> good afternoon
	xhtml = regex.sub(r"\b([Bb])ete noir", r"\1ête noir", xhtml)			# bete noir -> bête noir
	xhtml = regex.sub(r"\bEclat\b", r"Éclat", xhtml)				# Eclat -> Éclat
	xhtml = regex.sub(r"\beclat\b", r"éclat", xhtml)				# eclat -> éclat
	xhtml = regex.sub(r"\ba la\b", r"à la", xhtml)					# a la -> à la
	xhtml = regex.sub(r"\ba propos\b", r"apropos", xhtml)				# a propos -> apropos
	xhtml = regex.sub(r"\bper cent(s|ages?)?\b", r"percent\1", xhtml)		# per cent -> percent
	xhtml = regex.sub(r"\bpercent\.(\s+[\p{Lowercase_Letter}])", r"percent\1", xhtml)		# percent. followed by lowercase -> percent
	xhtml = regex.sub(r"\bpercent\.[,;:\!\?]", r"percent,", xhtml)			# per cent. -> percent
	xhtml = regex.sub(r"\b([Ee])ntree(s?)\b", r"\1ntrée\2", xhtml)			# entree -> entrée
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
	xhtml = regex.sub(r"\b([Ee])mploy[eé](s?)\b", r"\1mployee\2", xhtml)		# employé -> employee
	xhtml = regex.sub(r"\b(?<!ancien )([Rr])égime", r"\1egime", xhtml)		# régime -> regime (but "ancien régime")
	xhtml = regex.sub(r"\b([Bb])urthen", r"\1urden", xhtml)				# burthen -> burden
	xhtml = regex.sub(r"\b([Dd])isburthen", r"\1isburden", xhtml)			# disburthen -> disburden
	xhtml = regex.sub(r"\b([Uu])nburthen", r"\1nburden", xhtml)			# unburthen -> unburden
	xhtml = regex.sub(r"\b[EÉ]lys[eé]e", r"Élysée", xhtml)				# Elysee -> Élysée
	xhtml = regex.sub(r"\b([Ll])aw suit", r"\1awsuit", xhtml)			# law suit -> lawsuit
	xhtml = regex.sub(r"\bIncas(es?|ed|ing)", r"Encas\1", xhtml)			# Incase -> Encase
	xhtml = regex.sub(r"\bincas(es?|ed|ing)", r"encas\1", xhtml)			# incase -> encase
	xhtml = regex.sub(r"\bInclos(es?|ed?|ures?|ing)\b", r"Enclos\1", xhtml)		# Inclose -> Enclose
	xhtml = regex.sub(r"\binclos(es?|ed?|ures?|ing)\b", r"enclos\1", xhtml)		# inclose -> enclose
	xhtml = regex.sub(r"\b([Cc])ocoa[ -]?nut", r"\1oconut", xhtml)			# cocoanut / cocoa-nut -> coconut
	xhtml = regex.sub(r"\b([Ww])aggon", r"\1agon", xhtml)				# waggon -> wagon
	xhtml = regex.sub(r"\b([Ss])wop", r"\1wap", xhtml)				# swop -> swap
	xhtml = regex.sub(r"\b([Ll])acquey", r"\1ackey", xhtml)				# lacquey -> lackey
	xhtml = regex.sub(r"\b([Bb])ric-à-brac", r"\1ric-a-brac", xhtml)		# bric-à-brac -> bric-a-brac
	xhtml = regex.sub(r"\b([Kk])iosque", r"\1iosk", xhtml)				# kiosque -> kiosk
	xhtml = regex.sub(r"\b([Dd])[eé]pôt", r"\1epot", xhtml)				# depôt / dépôt -> depot
	xhtml = regex.sub(r"(?<![Cc]ompl)exion", r"ection", xhtml)			# -extion -> -exction (connexion, reflexion, etc., but "complexion")
	xhtml = regex.sub(r"\b([Dd])ulness", r"\1ullness", xhtml)			# dulness -> dullness
	xhtml = regex.sub(r"\b([Ff])iord", r"\1jord", xhtml)				# fiord -> fjord
	xhtml = regex.sub(r"\b([Ff])ulness\b", r"\1ullness", xhtml)			# fulness -> fullness (but not for ex. thoughtfulness)
	xhtml = regex.sub(r"['’]([Pp])hon(e|ing)", r"\1hon\2", xhtml)			# ’phone -> phone; note that we can't use \b on the left because it won't match for some reason
	xhtml = regex.sub(r"\b([Ss])hew", r"\1how", xhtml)				# shew -> show
	xhtml = regex.sub(r"\b([Tt])rowsers", r"\1rousers", xhtml)			# trowsers -> trousers
	xhtml = regex.sub(r"([Bb])iass", r"\1ias", xhtml)				# (un)biass(ed) -> (un)bias(ed)
	xhtml = regex.sub(r"\b([Cc])huse", r"\1hoose", xhtml)				# chuse -> choose
	xhtml = regex.sub(r"\b([Cc])husing", r"\1hoosing", xhtml)			# chusing -> choosing
	xhtml = regex.sub(r"\b([Cc])ontroul(s?)\b", r"\1ontrol\2", xhtml)		# controul -> control
	xhtml = regex.sub(r"\b([Cc])ontroul(ing|ed)", r"\1ontroll\2", xhtml)		# controuling/ed -> controlling/ed
	xhtml = regex.sub(r"\b([Ss])urpriz(e|ing)", r"\1urpris\2", xhtml)		# surprize->surprise, surprizing->surprising
	xhtml = regex.sub(r"\b([Dd])oat\b", r"\1ote", xhtml)				# doat -> dote
	xhtml = regex.sub(r"\b([Dd])oat(ed|ing)", r"\1ot\2", xhtml)			# doating -> doting
	xhtml = regex.sub(r"\b([Ss])topt", r"\1topped", xhtml)				# stopt -> stopped
	xhtml = regex.sub(r"\b([Ss])tept", r"\1tepped", xhtml)				# stept -> stepped
	xhtml = regex.sub(r"\b([Ss])ecresy", r"\1ecrecy", xhtml)			# secresy -> secrecy
	xhtml = regex.sub(r"\b([Mm])esalliance", r"\1ésalliance", xhtml)		# mesalliance -> mésalliance
	xhtml = regex.sub(r"\b([Ss])ate\b", r"\1at", xhtml)				# sate -> sat
	xhtml = regex.sub(r"\b([Aa])ttache\b", r"\1ttaché", xhtml)			# attache -> attaché
	xhtml = regex.sub(r"\b([Pp])orte(s?)[\- ]coch[eè]re(s?)\b", r"\1orte\2-cochère\3", xhtml)	# porte-cochere -> porte-cochère
	xhtml = regex.sub(r"\b([Nn])[eé]glig[eé]e?(s?)\b", r"\1egligee\2", xhtml)	# négligée -> negligee
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
	xhtml = regex.sub(r"\b[EÉ]cart[eé]\b", r"Écarté", xhtml)			# Ecarte -> Écarté
	xhtml = regex.sub(r"\b[eé]cart[eé]\b", r"écarté", xhtml)			# ecarte -> écarté
	xhtml = regex.sub(r"\b([Pp])ere\b", r"\1ère", xhtml)				# pere -> père (e.g. père la chaise)
	xhtml = regex.sub(r"\b([Tt])able(s?) d’hote\b", r"\1able\2 d’hôte", xhtml)	# table d'hote -> table d'hôte
	xhtml = regex.sub(r"\b([Ee])au(x?)[ \-]de[ \-]vie\b", r"\1au\2-de-vie", xhtml)	# eau de vie -> eau-de-vie
	xhtml = regex.sub(r"\b3d\b", r"3rd", xhtml)					# 3d -> 3rd (warning: check that we don't convert 3d in the "3 pence" sense!)
	xhtml = regex.sub(r"\b2d\b", r"2nd", xhtml)					# 2d -> 2nd (warning: check that we don't convert 2d in the "2 pence" sense!)
	xhtml = regex.sub(r"\b([Mm])ia[uo]w", r"\1eow", xhtml)				# miauw, miaow -> meow
	xhtml = regex.sub(r"\b([Cc])aviare", r"\1aviar", xhtml)				# caviare -> caviar
	xhtml = regex.sub(r"\b([Ss])ha’n’t", r"\1han’t", xhtml)				# sha'n't -> shan't (see https://english.stackexchange.com/questions/71414/apostrophes-in-contractions-shant-shant-or-shant)
	xhtml = regex.sub(r"\b([Ss])[uû]ret[eé]", r"\1ûreté", xhtml)			# Surete -> Sûreté
	xhtml = regex.sub(r"\b([Ss])eance", r"\1éance", xhtml)				# seance -> séance
	xhtml = regex.sub(r"\b([Ff])in[\- ]de[\- ]siecle", r"\1in de siècle", xhtml)	# fin de siecle -> fin de siècle
	xhtml = regex.sub(r"\bEmpale", r"Impale", xhtml)				# Empale -> Impale
	xhtml = regex.sub(r"\bempale", r"impale", xhtml)				# empale -> impale
	xhtml = regex.sub(r"\b([Tt])abu(s?)\b", r"\1aboo\2", xhtml)			# tabu -> taboo
	xhtml = regex.sub(r"\b([Kk])idnaping\b", r"\1idnapping", xhtml)			# kidnaping -> kidnapping
	xhtml = regex.sub(r"([,;a-z]\s)Quixotic\b", r"\1quixotic", xhtml)		# Quixotic -> quixotic but not at the start of a clause
	xhtml = regex.sub(r"([^\p{Lowercase_Letter}]’[Tt])\s(is|were|was|wasn’t|isn’t|ain’t)\b", r"\1\2", xhtml)		# 't is, 't was, 't were 't isn't -> 'tis, 'twas, 'twere, 't isn't
	xhtml = regex.sub(r"\b([Uu])p stairs\b", r"\1pstairs", xhtml)			# up stairs -> upstairs
	xhtml = regex.sub(r"(?<!up and )(?<!up or )\b([Dd])own stairs\b", r"\1ownstairs", xhtml)		# down stairs -> downstairs, but not "up (or|and) down stairs"
	xhtml = regex.sub(r"([Pp])artizan", r"\1artisan", xhtml)			# partizan -> partisan
	xhtml = regex.sub(r"([Nn])onplused", r"\1onplussed", xhtml)			# nonplused -> nonplussed
	xhtml = regex.sub(r"\b([Rr])eärrangement", r"\1earrangement", xhtml)		# reärrangement -> rearrangement
	xhtml = regex.sub(r"\b([Mm])untru(s?)\b", r"\1antra\2", xhtml)			# muntru -> mantra
	xhtml = regex.sub(r"\b([Hh])uzz(y|ies)\b", r"\1uss\2", xhtml)			# huzzy -> hussy
	xhtml = regex.sub(r"\b([Hh])iccough", r"\1iccup", xhtml)			# hiccough -> hiccup
	xhtml = regex.sub(r"\b([Rr])oue(s?)\b", r"\1oué\2", xhtml)			# roue -> roué
	xhtml = regex.sub(r"\b([Ii])dee fixe\b", r"\1dée fixe\2", xhtml)		# idee fixe -> idée fixe
	xhtml = regex.sub(r"\b([Ss])treet[\s\-]arab\b", r"\1treet Arab", xhtml)		# street-arab -> street Arab
	xhtml = regex.sub(r"\b[EÉ]migr[eé](?!e)", r"Émigré", xhtml)			# Emigre -> Émigré (but not emigrée, which is French)
	xhtml = regex.sub(r"\b[eé]migr[eé](?!e)", r"émigré", xhtml)			# emigre -> émigré (but not emigrée, which is French)
	xhtml = regex.sub(r"\b([Cc])ourtezan", r"\1ourtesan", xhtml)			# courtezan -> courtesan
	xhtml = regex.sub(r"\b([Cc])ompleate?", r"\1omplete", xhtml)			# compleat -> complete
	xhtml = regex.sub(r"\b([Dd])umfound", r"\1umbfound", xhtml)			# dumfound -> dumbfound
	xhtml = regex.sub(r"’([Cc])ello(s?)\b", r"\1ello\2", xhtml)			# 'cello -> cello
	xhtml = regex.sub(r"\bwelsh (rarebit|rabbit)\b", r"Welsh \1", xhtml)		# welsh rarebit/rabbit -> Welsh rarebit/rabbit
	xhtml = regex.sub(r"\b([Yy])our self\b(?!-)", r"\1ourself", xhtml)		# your self -> your self, but ignore constructs like `your self-determination` or `your selfish sister`.
	xhtml = regex.sub(r"\b([Aa])ny how\b", r"\1nyhow", xhtml)			# any how -> anyhow
	xhtml = regex.sub(r"\b([Aa])ny body\b", r"\1nybody", xhtml)			# any body -> anybody
	xhtml = regex.sub(r"\b([Ee])very body\b", r"\1verybody", xhtml)			# every body -> everybody
	xhtml = regex.sub(r"\bfrench window\b", r"French window", xhtml)		# french window -> French window
	xhtml = regex.sub(r"\b([Aa])n European", r"\1 European", xhtml)			# an European -> a European
	xhtml = regex.sub(r"\bProvencal", r"Provençal", xhtml)				# Provencal -> Provençal
	xhtml = regex.sub(r"\b([Rr])aison ([Dd])’etre", r"\1aison \2’être", xhtml)	# raison d'etre -> raison d'être
	xhtml = regex.sub(r"\b([Gg])arcon", r"\1arçon", xhtml)				# garcon -> garçon
	xhtml = regex.sub(r"\b([Cc])uracao", r"\1uraçao", xhtml)			# curacao -> curaçao
	xhtml = regex.sub(r"\b([Ss])oupcon", r"\1oupçon", xhtml)			# soupcon -> soupçon
	xhtml = regex.sub(r"\b([Tt])ouzle", r"\1ousle", xhtml)				# touzle(d) -> tousle(d)
	xhtml = regex.sub(r"\b([Cc])lientèle", r"\1lientele", xhtml)			# clientèle -> clientele
	xhtml = regex.sub(r"\b([Cc])ardamum", r"\1ardamom", xhtml)			# cardamum -> cardamom
	xhtml = regex.sub(r"\b([Ff])idgetted", r"\1idgeted", xhtml)			# fidgetted -> fidgeted
	xhtml = regex.sub(r"\b([Pp])ublick", r"\1ublic", xhtml)				# publick -> public
	xhtml = regex.sub(r"\b([Pp])rophane", r"\1rofane", xhtml)			# prophane -> profane
	xhtml = regex.sub(r"\b([Nn])o where", r"\1owhere", xhtml)			# no where -> nowhere
	xhtml = regex.sub(r"\b([Tt])yth", r"\1ith", xhtml)				# tythe -> tithe
	xhtml = regex.sub(r"\b([Ss])lily", r"\1lyly", xhtml)				# slily -> slyly
	xhtml = regex.sub(r"\b([Ff])oretel\b", r"\1oretell", xhtml)			# foretel -> foretell
	xhtml = regex.sub(r"\b([Cc])ypher", r"\1ipher", xhtml)				# cypher -> cipher
	# xhtml = regex.sub(r"\b([Dd])ivers\b", r"\1iverse", xhtml)			# divers -> diverse NOTE: these two are not the same word! https://www.merriam-webster.com/dictionary/divers "Divers is not a misspelling of diverse—it is a word in its own right."
	xhtml = regex.sub(r"\b([Ll])anthorn", r"\1antern", xhtml)			# lanthorn -> lantern
	xhtml = regex.sub(r"\b([Oo])rgie\b", r"\1rgy", xhtml)				# orgie -> orgy
	xhtml = regex.sub(r"\b([Oo])u?rang[\s-][Oo]utang?", r"\1rangutan", xhtml)	# ourang-outang -> orangutan
	xhtml = regex.sub(r"(?<!-)\b([Ss])o\sand\s([Ss])o\b(?!-)", r"\1o-and-\2o", xhtml)		# so and so -> so-and-so; ignore `so-and-so and so-and-so`
	xhtml = regex.sub(r"\b([Cc])añon", r"\1anyon", xhtml)				# cañon -> canyon
	xhtml = regex.sub(r"\b([Kk])vas\b", r"\1vass", xhtml)				# kvas -> kvass
	xhtml = regex.sub(r"\b([Pp])apier[-\s]mache\b", r"\1apier-mâché", xhtml)	# papier-mache -> papier-mâché
	xhtml = regex.sub(r"\b([Cc])yder\b", r"\1ider", xhtml)				# cyder -> cider
	xhtml = regex.sub(r"\b([Cc])onsomme", r"\1onsommé", xhtml)			# consomme -> consommé
	xhtml = regex.sub(r"\b([Cc])loath(s?)\b", r"\1lothe\2", xhtml)			# cloath(s) -> clothe(s)
	xhtml = regex.sub(r"\b([Cc])loath", r"\1loth", xhtml)				# cloath -> cloth(ed|ing|...)
	xhtml = regex.sub(r"\b([Pp])aultry", r"\1altry", xhtml)				# paultry -> paltry
	xhtml = regex.sub(r"\b([Bb])ye-?(word|law)", r"\1y\2", xhtml)			# bye-(word|law) -> by(word|law)
	xhtml = regex.sub(r"\btaylor", r"tailor", xhtml)				# taylor -> tailor (but not uppercase as it might be a last name
	xhtml = regex.sub(r"\b([Gg])ulph", r"\1ulf", xhtml)				# gulph -> gulf
	xhtml = regex.sub(r"\b([Mm])usicke?\b", r"\1usic", xhtml)			# musick -> music
	xhtml = regex.sub(r"\b([Ee])very where\b", r"\1verywhere", xhtml)		# every where -> everywhere
	xhtml = regex.sub(r"\b([Aa])ny where\b", r"\1nywhere", xhtml)			# any where -> anywhere
	xhtml = regex.sub(r"\b([Ee])very thing\b", r"\1verything", xhtml)		# every thing -> everything
	xhtml = regex.sub(r"\b([Aa])ny thing\b", r"\1nything", xhtml)			# any thing -> anything
	xhtml = regex.sub(r"\b([Rr])e-?enforce", r"\1einforce", xhtml)			# re-enforce -> reinforce
	xhtml = regex.sub(r"\b([Ll])uny", r"\1oony", xhtml)				# luny -> loony
	xhtml = regex.sub(r"\b([Ll])unies", r"\1oonies", xhtml)				# lunies -> loonies
	xhtml = regex.sub(r"\b([Vv])icuna", r"\1icuña", xhtml)				# vicuna -> vicuña
	xhtml = regex.sub(r"\b([Cc])larionet", r"\1larinet", xhtml)			# clarionet -> clarinet
	xhtml = regex.sub(r"\b([Bb])ye?[\- ]the[\- ]bye?\b", r"\1y the by", xhtml)	# by-the-bye -> by the by
	xhtml = regex.sub(r"\b([Ss])pung", r"\1pong", xhtml)				# spung(e|ing|y) -> sponge
	xhtml = regex.sub(r"\b([Ww])oful", r"\1oeful", xhtml)				# woful -> woeful
	xhtml = regex.sub(r"\b([Hh]e|[Ss]he|[Yy]ou|[Tt]hey)’ld", r"\1’d", xhtml)	# he'ld, she'ld, you'ld, they'ld -> he'd, she'd, you'd, they'd
	xhtml = regex.sub(r"\b([Mm])ean time", r"\1eantime", xhtml)			# mean time -> meantime
	xhtml = regex.sub(r"\b([Ch])huck[\- ]full\b", r"\1ock-full", xhtml)		# chuck-full -> chock-full
	xhtml = regex.sub(r"\b([Pp])rythee\b", r"\1rithee", xhtml)			# prythee -> prithee
	xhtml = regex.sub(r"\b([Hh])av’n’t", r"\1aven’t", xhtml)			# hav’n’t -> haven’t
	xhtml = regex.sub(r"\b([Bb])awble", r"\1auble", xhtml)				# bawble -> bauble
	xhtml = regex.sub(r"\b([Pp])iny?on(s?)\b", r"\1iñon\2", xhtml)			# pinyon -> piñon
	xhtml = regex.sub(r"\b([Ii])kon(s?)\b", r"\1con\2", xhtml)			# ikon -> icon
	xhtml = regex.sub(r"\b([Pp])remiss\b", r"\1remise", xhtml)			# premiss -> premise
	xhtml = regex.sub(r"\b([Pp])remisses", r"\1remises", xhtml)			# premisses -> premises
	xhtml = regex.sub(r"\b([Rr])icketty", r"\1ickety", xhtml)			# ricketty -> rickety
	xhtml = regex.sub(r"\b([Dd])[ié]shabille", r"\1eshabille", xhtml)		# déshabille -> deshabille
	xhtml = regex.sub(r"\b([Mm])ollah", r"\1ullah", xhtml)				# mollah -> mullah
	xhtml = regex.sub(r"\b([Ss])opha(s?)\b", r"\1opha\2", xhtml)			# sopha -> sofa
	xhtml = regex.sub(r"\b([Oo])dalisk", r"\1dalisque", xhtml)			# odalisk -> odalisque
	xhtml = regex.sub(r"\b([Ss])cissar", r"\1cissor", xhtml)			# scissar -> scissor
	xhtml = regex.sub(r"\b([Aa])lmanack", r"\1lmanac", xhtml)			# almanack -> almanac
	xhtml = regex.sub(r"\b([Nn])egociation", r"\1egotiation", xhtml)		# negociation -> negotiation
	xhtml = regex.sub(r"Incumber", r"Encumber", xhtml)				# incumber -> encumber
	xhtml = regex.sub(r"incumber", r"encumber", xhtml)				# incumber -> encumber
	xhtml = regex.sub(r"\bCadi\b", r"Qadi", xhtml)					# cadi -> qadi
	xhtml = regex.sub(r"\bcadi\b", r"qadi", xhtml)					# cadi -> qadi
	xhtml = regex.sub(r"\bSoldan(s?)\b", r"Sultan\1", xhtml)			# soldan -> sultan
	xhtml = regex.sub(r"\bsoldan(s?)\b", r"sultan\1", xhtml)			# soldan -> sultan
	xhtml = regex.sub(r"\b([Pp])edler", r"\1eddler", xhtml)				# pedler -> peddler
	xhtml = regex.sub(r"\b([Cc])aldron(s?)", r"\1auldron\2", xhtml)			# caldron -> cauldron
	xhtml = regex.sub(r"\b([Tt])hru\b", r"\1hru", xhtml)				# thru -> through
	xhtml = regex.sub(r"\b[‘’]([Ss])cope(s?)\b", r"\1cope\2", xhtml)		# 'scope -> scope
	xhtml = regex.sub(r"\b([Ff])(aqu?ir|akeer)", r"\1akir", xhtml)			# faqir, fakeer -> fakir
	xhtml = regex.sub(r"\b([Ii])maum", r"\1mam", xhtml)				# imaum -> imam
	xhtml = regex.sub(r"\b([Mm])o?ujik", r"\1uzhik", xhtml)				# moujik/mujik -> muzhik
	xhtml = regex.sub(r"\b([Cc])har[ -][aà][ -]banc", r"\1harabanc", xhtml)		# char-à-banc -> charabanc
	xhtml = regex.sub(r"’([Cc])ellist", r"\1ellist", xhtml)				# 'cellist -> cellist
	xhtml = regex.sub(r"([Pp])ourtray", r"\1ortray", xhtml)				# pourtray -> portray
	xhtml = regex.sub(r"([S])toopid", r"\1tupid", xhtml)				# stoopid -> stupid
	xhtml = regex.sub(r"([S])uède", r"\1uede", xhtml)				# suède -> suede
	xhtml = regex.sub(r"([Ff])or ever\b(?!\s+so long)",r"\1orever", xhtml)		# for ever -> forever
	xhtml = regex.sub(r"([Dd])ébris\b", r"\1ebris", xhtml)				# débris -> debris
	xhtml = regex.sub(r"\b([Tt])ho(['’]|\b)(?!\.</abbr>)", r"\1hough", xhtml)	# tho' -> though
	xhtml = regex.sub(r"\b([Aa])ntient", r"\1ncient", xhtml)			# antient -> ancient
	xhtml = regex.sub(r"\b([Bb])efal(s?)\b", r"\1efall\2", xhtml)			# befal -> befall
	xhtml = regex.sub(r"\b([Tt])enour", r"\1enor", xhtml)				# tenor -> tenour
	xhtml = regex.sub(r"\b([Rr])ibb?and", r"\1ibbon", xhtml)			# ribband -> ribbon (note: `ribband` has a legitimate 2nd meaning but it's extremely rare)
	xhtml = regex.sub(r"\b([Gg])rewsome", r"\1ruesome", xhtml)			# grewsome -> gruesome
	xhtml = regex.sub(r"([^’]\b[Tt])il\b", r"\1ill", xhtml)				# til -> till (but not 'til which can look more natural in dialect)
	xhtml = regex.sub(r"\b([Cc])hear", r"\1heer", xhtml)				# chear -> cheer
	xhtml = regex.sub(r"\bcentinel", r"sentinel", xhtml)				# centinel -> sentinel
	xhtml = regex.sub(r"\bCentinel", r"Sentinel", xhtml)				# centinel -> sentinel
	xhtml = regex.sub(r"\b([Ss])e’nnight", r"\1ennight", xhtml)			# se'nnight -> sennight
	xhtml = regex.sub(r"\b([Pp])aroquet", r"\1arakeet", xhtml)			# paroquet -> parakeet
	xhtml = regex.sub(r"\b([Rr])isque\b", r"\1isqué", xhtml)			# risque -> risqué
	xhtml = regex.sub(r"\b([Ff])rolick\b", r"\1rolic", xhtml)			# frolick -> frolic
	xhtml = regex.sub(r"\bIncroach", r"Encroach", xhtml)				# Incroach -> Encroach
	xhtml = regex.sub(r"\bincroach", r"encroach", xhtml)				# incroach -> encroach
	xhtml = regex.sub(r"\bmizen ?mast", r"mizzenmast", xhtml)			# mizenmast -> mizzenmast
	xhtml = regex.sub(r"\bbefal(s?)\b", r"befall\1", xhtml)				# befal -> befall
	xhtml = regex.sub(r"\bto a [‘“]?[Tt]([^’”]?)[’”]?(\s)", r"to a T\1\2", xhtml)		# Remove quotes from `to a T` and capitalize T
	xhtml = regex.sub(r"\b([Tt])eaze", r"\1ease", xhtml)				# teaze -> tease
	xhtml = regex.sub(r"\b([Cc])hrystal", r"\1rystal", xhtml)			# chrystal -> crystal
	xhtml = regex.sub(r"\b([Pp])art[iy]-?colo(u?)r", r"\1arti-colo\2r", xhtml)	# party-color -> parti-color
	xhtml = regex.sub(r"\b([Aa])ukward", r"\1wkward", xhtml)			# aukward -> awkward
	xhtml = regex.sub(r"\b([Aa])lledg(ing|e[sd])", r"\1lleg\2", xhtml)		# alledge -> allege
	xhtml = regex.sub(r"\b([Hh])er’s", r"\1ers", xhtml)				# her's -> hers
	xhtml = regex.sub(r"\b([Pp])igm(y|ies)", r"\1ygm\2", xhtml)			# pigmy -> pygmy
	xhtml = regex.sub(r"\bencreas", r"increas", xhtml)				# encreas(e|ing) -> increas(e|ing)
	xhtml = regex.sub(r"\bEncreas", r"Increas", xhtml)				# encreas(e|ing) -> increas(e|ing)
	xhtml = regex.sub(r"\b([Ee])nterpriz", r"\1nterpris", xhtml)			# enterprize -> enterprise
	xhtml = regex.sub(r"\b([Ff])ye\b", r"\1ie", xhtml)				# fye -> fie
	xhtml = regex.sub(r"\b([Cc])hace(s|d)?\b", r"\1hase\2", xhtml)			# chace -> chase
	xhtml = regex.sub(r"\b([Ss])pight", r"\1pite", xhtml)				# spight -> spite
	xhtml = regex.sub(r"\b([Ss])tedfast", r"\1teadfast", xhtml)			# stedfast -> steadfast
	xhtml = regex.sub(r"\b([Rr])elique", r"\1elic", xhtml)				# relique -> relic
	xhtml = regex.sub(r"\b([Ll])agune", r"\1agoon", xhtml)				# lagune -> lagoon
	xhtml = regex.sub(r"\b([Ss])irup", r"\1yrup", xhtml)				# sirup -> syrup
	xhtml = regex.sub(r"\b([Bb])ye-?way", r"\1yway", xhtml)				# bye-way -> byway
	xhtml = regex.sub(r"\b([Bb])efel\b", r"\1efell", xhtml)				# befel -> befell
	xhtml = regex.sub(r"\b([Vv])illan(ies|ous)", r"\1illain\2", xhtml)		# villanies/villainous -> villainies/villainous
	xhtml = regex.sub(r"\b([Bb])rand([\- ])new\b", r"\1rand\2new", xhtml)		# bran new -> brand new
	xhtml = regex.sub(r"\b([Mm])illionnaire", r"\1illionaire", xhtml)		# millionnaire -> millionaire
	xhtml = regex.sub(r"['’]([Pp])ossum", r"\1ossum", xhtml)			# 'possum -> possum
	xhtml = regex.sub(r"\b([Uu])nder weigh\b", r"\1nderway", xhtml)			# under weigh -> underway
	xhtml = regex.sub(r"\bQuire(s?)\b", r"Choir\1", xhtml)				# quire -> choir
	xhtml = regex.sub(r"\bquire(s?)\b", r"choir\1", xhtml)				# quire -> choir
	xhtml = regex.sub(r"\b([Bb])onâ fide\b", r"\1ona fide", xhtml)			# bonâ fide -> bona fide
	xhtml = regex.sub(r"\b([Hh])alf [Ww]ay\b", r"\1alfway", xhtml)			# half way -> halfway
	xhtml = regex.sub(r"\b([Tt])hreshhold", r"\1hreshold", xhtml)			# threshhold -> threshold

	# Normalize some names
	xhtml = regex.sub(r"Moliere", r"Molière", xhtml)				# Moliere -> Molière
	xhtml = regex.sub(r"Tolstoi", r"Tolstoy", xhtml)				# Tolstoi -> Tolstoy
	xhtml = regex.sub(r"Dostoi?e(v|ff)sky", r"Dostoevsky", xhtml)			# Dostoievsky -> Dostoevsky
	xhtml = regex.sub(r"Buonaparte", r"Bonaparte", xhtml)				# Buonaparte -> Bonaparte
	xhtml = regex.sub(r"Shake?spea?r([^ie])", r"Shakespeare\1", xhtml)		# Shakespear/Shakspeare -> Shakespeare
	xhtml = regex.sub(r"Shake?spea?re", r"Shakespeare", xhtml)			# Shakespear/Shakspeare -> Shakespeare
	xhtml = regex.sub(r"Shakspea?rean", r"Shakespearean", xhtml)			# Shaksperean -> Shakespearean
	xhtml = regex.sub(r"Shakspea?re?’s", r"Shakespeare’s", xhtml)			# Shakspere’s -> Shakespeare’s
	xhtml = regex.sub(r"Raffaelle", r"Raphael", xhtml)				# Raffaelle -> Raphael
	xhtml = regex.sub(r"Michael[\- ]?[Aa]ngelo", r"Michelangelo", xhtml)		# Michael Angelo -> Michelangelo
	xhtml = regex.sub(r"\bVergil", r"Virgil", xhtml)				# Vergil -> Virgil
	xhtml = regex.sub(r"\bVishnoo", r"Vishnu", xhtml)				# Vishnoo -> Vishnu
	xhtml = regex.sub(r"\bPekin\b", r"Peking", xhtml)				# Pekin -> Peking
	xhtml = regex.sub(r"\bBuenos Ayres\b", r"Buenos Aires", xhtml)			# Buenos Ayres -> Buenos Aires
	xhtml = regex.sub(r"\bCracow", r"Krakow", xhtml)				# Cracow -> Krakow
	xhtml = regex.sub(r"\bKieff?\b", r"Kiev", xhtml)				# Kief -> Kiev
	xhtml = regex.sub(r"\bRo?umania", r"Romania", xhtml)				# Roumania(n) -> Romania(n)
	xhtml = regex.sub(r"\b([Rr])enascence", r"\1enaissance", xhtml)			# renascence -> renaissance
	xhtml = regex.sub(r"\bThibet", r"Tibet", xhtml)					# Thibet -> Tibet
	xhtml = regex.sub(r"\bTimbuctoo", r"Timbuktu", xhtml)				# Timbuctoo -> Timbuktu
	xhtml = regex.sub(r"\bTokio", r"Tokyo", xhtml)					# Tokio -> Tokyo
	xhtml = regex.sub(r"\bT?[Cc]hekh?o(v|ff)", r"Chekhov", xhtml)			# Tchekhov/Chekov/Chekoff -> Chekhov
	xhtml = regex.sub(r"\bVereshtchagin", r"Vereshchagin", xhtml)			# Vereshtchagin -> Vereshchagin
	xhtml = regex.sub(r"\bSoudan", r"Sudan", xhtml)					# Soudan -> Sudan
	xhtml = regex.sub(r"\bJack-in-the-box", r"jack-in-the-box", xhtml)		# Jack-in-the-box -> jack-in-the-box
	xhtml = regex.sub(r"\bServia", r"Serbia", xhtml)				# Servia(n) -> Serbia(n)
	xhtml = regex.sub(r"\bEsquimaux?\b", r"Eskimo", xhtml)				# Esquimau -> Eskimo
	xhtml = regex.sub(r"\bLaocoon", r"Laocoön", xhtml)				# Lacoon -> Laocoön
	xhtml = regex.sub(r"Porto Rico", r"Puerto Rico", xhtml)				# Porto Rico -> Puerto Rico
	xhtml = regex.sub(r"Mahomet", r"Muhammad", xhtml)				# Mahomet -> Muhammad
	xhtml = regex.sub(r"M[ao]hommed", r"Muhammad", xhtml)		        	# Mahommed -> Muhammad
	xhtml = regex.sub(r"Esthonia(n?)", r"Estonia\1", xhtml)				# Esthonia(n) -> Estonia(n)
	xhtml = regex.sub(r"\b([Ss])anscrit\b", r"\1anskrit", xhtml)			# Sanscrit -> Sanskrit
	xhtml = regex.sub(r"Francois", r"François", xhtml)				# Francois -> François
	xhtml = regex.sub(r"Hayti(\b|an\b)", r"Haiti\1", xhtml)				# Hayti -> Haiti
	xhtml = regex.sub(r"Zymbabwe", r"Zimbabwe", xhtml)				# Zymbabwe -> Zimbabwe
	xhtml = regex.sub(r"Moslem(s?)\b", r"Muslim\1", xhtml)				# Moslem -> Muslim, but stop at a word break for `Moslemin`, a rare word that has no modern spelling equivalent
	xhtml = regex.sub(r"Bronte\b", r"Brontë", xhtml)				# Bronte -> Brontë
	xhtml = regex.sub(r"Leipsick?\b", r"Leipzig", xhtml)				# Leipsic -> Leipzig; note that there are some US cities actually named `Leipsic`!
	xhtml = regex.sub(r"Gengis", r"Genghis", xhtml)					# Gengis -> Genghis
	xhtml = regex.sub(r"Hamburgh", r"Hamburg", xhtml)				# Hamburgh -> Hamburg
	xhtml = regex.sub(r"Dant[sz]ick?", r"Danzig", xhtml)				# Dantsic -> Danzig
	xhtml = regex.sub(r"Barbadoes", r"Barbados", xhtml)				# Barbadoes -> Barbados
	xhtml = regex.sub(r"jesuit", r"Jesuit", xhtml)					# jesuit -> Jesuit
	xhtml = regex.sub(r"Roman catholic", r"Roman Catholic", xhtml)			# Roman catholic -> Roman Catholic; Note that we can't uppercase `catholic` in the generic sense because `catholic` can mean "worldly"
	xhtml = regex.sub(r"Burmah", r"Burma", xhtml)					# Burmah -> Burma
	xhtml = regex.sub(r"Turgenieff", r"Turgenev", xhtml)				# Turgenieff -> Turgenev
	xhtml = regex.sub(r"Gizeh", r"Giza", xhtml)					# Gizeh -> Giza
	xhtml = regex.sub(r"Fee?jee", r"Fiji", xhtml)					# Feejee -> Fiji
	xhtml = regex.sub(r"[YJ]edd?o\b", r"Edo", xhtml)				# Yeddo/Jeddo -> Edo
	xhtml = regex.sub(r"Pesth\b", r"Pest", xhtml)					# Pesth -> Pest, i.e. Buda-Pest
	xhtml = regex.sub(r"Buda-Pest\b", r"Budapest", xhtml)				# Buda-Pest -> Budapest
	xhtml = regex.sub(r"Chili(\b|an\b)\b", r"Chile\1", xhtml)			# Chili -> Chile
	xhtml = regex.sub(r"(?<![\.!\?])\sAl-([A-Z])", r" al-\1", xhtml)		# Lowercase Arabic definite article (e.g. Al-Zubayr -> al-Zubayr) in the middle of a sentence
	xhtml = regex.sub(r"\bSion\b", r"Zion", xhtml)					# Sion -> Zion

	# Remove archaic diphthongs
	xhtml = regex.sub(r"\b([Mm])edi(æ|ae)val", r"\1edieval", xhtml)
	xhtml = xhtml.replace("Cæsar", r"Caesar")
	xhtml = xhtml.replace("Crœsus", r"Croesus")
	xhtml = xhtml.replace("\bæon\b", r"aeon")
	xhtml = xhtml.replace("\bÆon\b", r"Aeon")
	xhtml = xhtml.replace("Æneas", r"Aeneas")
	xhtml = xhtml.replace("Æneid", r"Aeneid")
	xhtml = xhtml.replace("Æschylus", r"Aeschylus")
	xhtml = xhtml.replace("æsthet", r"aesthet") # aesthetic, aesthete, etc.
	xhtml = xhtml.replace("Æsthet", r"Aesthet") # Aesthetic, Aesthete, etc.
	xhtml = regex.sub(r"\b([Hh])yæna", r"\1yena", xhtml)
	xhtml = regex.sub(r"\b([Ll])arvæ", r"\1arvae", xhtml)
	xhtml = xhtml.replace("Œdip", r"Oedip") # Oedipus, Oedipal
	xhtml = regex.sub(r"\b([Pp])æan", r"\1aean", xhtml)
	xhtml = regex.sub(r"\b([Vv])ertebræ", r"\1ertebrae", xhtml)
	xhtml = xhtml.replace("Linnæus", r"Linnaeus")
	xhtml = regex.sub(r"\b([Ff])œtus", r"\1oetus", xhtml)

	# Remove spaces before contractions like `n’t` e.g. `is n’t` -> `isn’t`
	xhtml = regex.sub(r" n’t\b", r"n’t", xhtml)

	# Remove spaces before contractions like `it 'll`
	xhtml = regex.sub(r"([\p{Letter}])\s[‘’]ll\b", r"\1’ll", xhtml)

	# Remove roman ordinals
	xhtml = regex.sub(r"<span epub:type=\"z3998:roman\">(.*?)</span>(st|nd|rd|th)\b", r'<span epub:type="z3998:roman">\1</span>', xhtml)

	# X-ray is always capitalized. Match a preceding space so that we don't catch it in an ID attribute.
	xhtml = regex.sub(r"([\p{Punctuation}\s])x-ray", r"\1X-ray", xhtml)

	# Replace 2d with 2nd and 3d with 3rd
	# Check for a following abbr because `3<abbr>d.</abbr>` could mean `3 pence`
	xhtml = regex.sub(r"\b([0-9]*2)d(?!</abbr>)", r"\1nd", xhtml)
	xhtml = regex.sub(r"\b([0-9]*3)d(?!</abbr>)", r"\1rd", xhtml)

	# Canadian spelling follows US
	if language in ["en-US", "en-CA"]:
		xhtml = regex.sub(r"\b([Cc])osey", r"\1ozy", xhtml)

	# Australian and Irish spelling follows GB
	if language in ["en-GB", "en-AU", "en-IE"]:
		xhtml = regex.sub(r"\b([Cc])osey", r"\1osy", xhtml)

	# US spelling is unique
	if language == "en-US":
		xhtml = regex.sub(r"\b([Mm])anœuvred", r"\1aneuvered", xhtml)
		xhtml = regex.sub(r"\b([Mm])anœuv(?:er|re)", r"\1aneuver", xhtml) # Omit last letter to catch both maneuverS and maneuverING
		xhtml = regex.sub(r"\b([Mm])anœuvering", r"\1aneuvering", xhtml)
	else:
		xhtml = regex.sub(r"\b([Mm])anœuvred", r"\1anoeuvred", xhtml)
		xhtml = regex.sub(r"\b([Mm])anœuv(?:er|re)", r"\1anoeuvre", xhtml)
		xhtml = regex.sub(r"\b([Mm])anœuvring", r"\1anoeuvring", xhtml)
		xhtml = regex.sub(r"\b([Mm])anoeuvreing", r"\1anoeuvring", xhtml)

	return xhtml
