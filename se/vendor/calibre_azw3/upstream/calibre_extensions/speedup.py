import os

def barename(value):
	return value.rpartition('}')[-1]

def namespace(value):
	if value.startswith('{'):
		return value[1:].partition('}')[0]
	return ''

def clean_xml_chars(value):
	return ''.join(character for character in value if character in '\t\n\r' or ord(character) >= 32)

def pread_all(file_descriptor, size, offset):
	return os.pread(file_descriptor, size, offset)
