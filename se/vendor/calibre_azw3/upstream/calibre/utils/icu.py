import unicodedata
import re

def lower(value):
	return value.lower() if value is not None else value

def upper(value):
	return value.upper() if value is not None else value

def title_case(value):
	return value.title() if value is not None else value

def capitalize(value):
	return value.capitalize() if value is not None else value

def sort_key(value):
	return lower(value or '')

def numeric_sort_key(value):
	return tuple(int(piece) if piece.isdigit() else piece.lower() for piece in re.split(r'(\d+)', value or ''))
primary_sort_key = sort_key
case_sensitive_sort_key = lambda value: value or ''

def strcmp(first, second):
	return (sort_key(first) > sort_key(second)) - (sort_key(first) < sort_key(second))

case_sensitive_strcmp = strcmp
primary_strcmp = strcmp

def safe_chr(value):
	return chr(value)

def ord_string(value):
	return tuple(map(ord, value))

def normalize(value, mode='NFC'):
	return unicodedata.normalize(mode, value)

def remove_accents_icu(value):
	return ''.join(character for character in unicodedata.normalize('NFKD', value) if not unicodedata.combining(character))

remove_accents_regex = remove_accents_icu
