import html

def replace_all_entities(value, is_xml=False):
	if isinstance(value, bytes):
		return html.unescape(value.decode('utf-8')).encode('utf-8')
	return html.unescape(value)
