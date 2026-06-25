from calibre.customize.profiles import input_profiles as _input_profiles
from calibre.customize.profiles import output_profiles as _output_profiles

def input_profiles():
	return tuple(profile(None) for profile in _input_profiles)

def output_profiles():
	return tuple(profile(None) for profile in _output_profiles)

def available_input_formats():
	return {'epub'}

def available_output_formats():
	return {'azw3'}

def plugin_for_input_format(file_type):
	if file_type == 'epub':
		from calibre.ebooks.conversion.plugins.epub_input import EPUBInput
		return EPUBInput(None)
	return None

def plugin_for_output_format(file_type):
	if file_type == 'azw3':
		from calibre.ebooks.conversion.plugins.mobi_output import AZW3Output
		return AZW3Output(None)
	return None

def run_plugins_on_preprocess(path, file_type=None):
	return path

def run_plugins_on_postprocess(path, file_type=None):
	return None

def all_metadata_plugins():
	return ()

def metadata_plugins():
	return ()
