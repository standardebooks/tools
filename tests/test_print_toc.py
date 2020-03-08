"""
Test the print-toc command and related functions
"""

from pathlib import Path
from bs4 import BeautifulSoup
from helpers import assemble_book, must_run, output_is_golden
from se.se_epub_generate_toc import add_landmark


def test_print_toc(data_dir: Path, draft_dir: Path, work_dir: Path, update_golden: bool, capfd):
	"""Verify the expected TOC is generated from test book"""
	text_dir = data_dir / "print-toc" / "in"
	book_dir = assemble_book(draft_dir, work_dir, text_dir)

	must_run(f"se print-toc {book_dir}")

	out, err = capfd.readouterr()
	assert err == ""

	golden_file = data_dir / "print-toc" / "toc-out.txt"
	assert output_is_golden(out, golden_file, update_golden)

def test_add_landmark_no_title():
	"""Verify we can find a landmark title when no title element is present"""
	soup = BeautifulSoup('<html><body><section epub:type="foo"><h1></h1></section></body></html>', features="lxml")
	landmarks = []
	add_landmark(soup, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_with_title():
	"""Verify we can find a landmark title when title element is present"""
	soup = BeautifulSoup('<html><head><title>Bar</title><body><section epub:type="foo"><h1></h1></section></body></html>', features="lxml")
	landmarks = []
	add_landmark(soup, "file", landmarks)

	assert landmarks[0].title == "Bar"

def test_add_landmark_empty_title():
	"""Verify we can find a landmark title when title element is empty"""
	soup = BeautifulSoup('<html><head><title></title><body><section epub:type="foo"><h1></h1></section></body></html>', features="lxml")
	landmarks = []
	add_landmark(soup, "file", landmarks)

	assert landmarks[0].title == "Foo"
