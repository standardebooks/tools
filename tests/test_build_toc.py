"""
Test the build-toc command and related functions
"""

from pathlib import Path
from helpers import assemble_book, must_run, output_is_golden
from se.se_epub_generate_toc import add_landmark
import se.easy_xml


def test_build_toc(data_dir: Path, draft_dir: Path, work_dir: Path, update_golden: bool, capfd):
	"""Verify the expected TOC is generated from test book"""
	text_dir = data_dir / "build-toc" / "in"
	book_dir = assemble_book(draft_dir, work_dir, text_dir)

	must_run(f"se build-toc --stdout {book_dir}")

	out, err = capfd.readouterr()
	assert err == ""

	golden_file = data_dir / "build-toc" / "toc-out.txt"
	assert output_is_golden(out, golden_file, update_golden)

def test_add_landmark_no_title():
	"""Verify we can find a landmark title when no title element is present"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_with_title():
	"""Verify we can find a landmark title when title element is present"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title>Bar</title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Bar"

def test_add_landmark_empty_title():
	"""Verify we can find a landmark title when title element is empty"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title></title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"
