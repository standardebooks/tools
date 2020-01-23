"""
Tests for simple se commands that just output to stdout and don't require
a book as input.
"""

import pytest

import se
from helpers import must_run

SIMPLE_CMDS = [
    ("dec2roman", "1 4 7 45 900", "I\nIV\nVII\nXLV\nCM"),
    ("dec2roman", "1867", "MDCCCLXVII"),
    ("roman2dec", "III XXV LXXVI CXLII DCCCLXIV", "3\n25\n76\n142\n864"),
    ("roman2dec", "MDCCLXXVI", "1776"),
    ("make-url-safe", "http://google.com", "http-google-com"),
    ("make-url-safe", "abc123.!-+d  xyz ", "abc123-d\nxyz"),
    ("titlecase", "'the Mysterious Affair At styles'", "The Mysterious Affair at Styles"),
    ("titlecase", "heart of darkness", "Heart\nOf\nDarkness"),
]

@pytest.mark.parametrize("cmd_name, cmd_args, cmd_out", SIMPLE_CMDS)
def test_simple_cmds(cmd_name: str, cmd_args: str, cmd_out: str, capfd):
	"""Execute command and check output"""
	must_run("se {} {}".format(cmd_name, cmd_args))
	out, _ = capfd.readouterr()
	assert cmd_out == out.rstrip()

def test_unicode_names(capfd):
	"""Verify that the unicode-names command has the expected output"""
	must_run("se unicode-names foo")
	out, _ = capfd.readouterr()
	expected = "f\tU+0066\tLATIN SMALL LETTER F\thttp://unicode.org/cldr/utility/character.jsp?a=0066\no\tU+006F\tLATIN SMALL LETTER O\thttp://unicode.org/cldr/utility/character.jsp?a=006F\no\tU+006F\tLATIN SMALL LETTER O\thttp://unicode.org/cldr/utility/character.jsp?a=006F\n"
	assert expected == out

def test_version(capfd):
	"""Verify that the version command returns the version"""
	must_run("se version")
	out, _ = capfd.readouterr()
	assert out.startswith(se.VERSION)

def test_help(capfd):
	"""Verify that the help command returns without an error"""
	must_run("se help")
	out, _ = capfd.readouterr()
	assert out.splitlines()[0] == "The following commands are available:"
