#!/usr/bin/env python3

import sys
from termcolor import colored


MESSAGE_INDENT = "    "
UNICODE_BOM = "\ufeff"
IGNORED_FILES = ["colophon.xhtml", "titlepage.xhtml", "imprint.xhtml", "uncopyright.xhtml", "halftitle.xhtml", "toc.xhtml", "loi.xhtml"]
XHTML_NAMESPACES = {"xhtml": "http://www.w3.org/1999/xhtml", "epub": "http://www.idpf.org/2007/ops", "z3998": "http://www.daisy.org/z3998/2012/vocab/structure/", "se": "https://standardebooks.org/vocab/1.0", "dc": "http://purl.org/dc/elements/1.1/", "opf": "http://www.idpf.org/2007/opf"}


def print_error(message, verbose=False):
	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Error:", "red", attrs=["reverse"]), message), file=sys.stderr)

def print_warning(message, verbose=False):
	print("{}{} {}".format(MESSAGE_INDENT if verbose else "", colored("Warning:", "yellow", attrs=["reverse"]), message))

def print_line_after_warning(message, verbose=False):
	print("{}         {}{}".format(MESSAGE_INDENT if verbose else "", MESSAGE_INDENT, message))
