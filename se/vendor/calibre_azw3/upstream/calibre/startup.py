import builtins

builtins.__dict__['_'] = lambda value: value
builtins.__dict__['__'] = lambda value: value
builtins.__dict__['dynamic_property'] = lambda function: function(None)
builtins.__dict__['lopen'] = open

def initialize_calibre() -> None:
	return
