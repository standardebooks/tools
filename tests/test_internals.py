"""
Test internal SE programming functions
"""

from pathlib import Path

import regex

from se.se_epub_generate_toc import add_landmark
import se.easy_xml
from se.se_epub_lint import SourceFile


XML_COMMENT_PATTERN = regex.compile(r"<!--.+?-->", flags=regex.DOTALL)

def test_add_landmark_empty_title():
	"""
	Verify we can find a landmark title when title element is present but empty.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title></title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_no_title():
	"""
	Verify we can find a landmark title when title element is not present.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Foo"

def test_add_landmark_with_title():
	"""
	Verify we can find a landmark title when title element is present.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/, se: https://standardebooks.org/vocab/1.0" xml:lang="en-US"><head><title>Bar</title></head><body><section epub:type="foo"><h1></h1></section></body></html>')
	landmarks = []
	add_landmark(dom, "file", landmarks)

	assert landmarks[0].title == "Bar"

def test_inner_text():
	"""
	Verify that inner_text strips leading and trailing whitespace from the root
	element, retains interior whitespace, excludes all tags and attributes, and
	returns both named and numeric entities as their corresponding characters.
	"""
	dom = se.easy_xml.EasyXmlTree('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-US"><body><p epub:type="foo"> a <i>&lt;</i>b <span epub:type="bar">\t&#913; </span>c<br/>\nd </p>e</body></html>')
	p = dom.xpath("//p")[0]

	assert p.inner_text() == "a <b \tΑ c\nd"

def test_line_numbers_no_comments():
	"""
	Verify line number offset calculations without comments.
	"""
	contents = """\
<p>L1</p>
<p>L2</p>
<p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_leading_comments():
	"""
	Verify line number offset calculations with leading comments.
	"""
	contents = """\
<!-- C1 --><p>L1</p>
<!-- C2 --><p>L2</p>
<!-- C3 --><p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_trailing_comments():
	"""
	Verify line number offset calculations with trailing comments.
	"""
	contents = """\
<p>L1</p><!-- C1 -->
<p>L2</p><!-- C2 -->
<p>L3</p><!-- C3 -->"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_inline_comments():
	"""
	Verify line number offset calculations with inline comments.
	"""
	contents = """\
<p>L1<!-- C1 --></p>
<p><!-- C2 -->L2</p>
<p>L3</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (20, 3)]

def test_line_numbers_line_comments():
	"""
	Verify line number offset calculations with full line comments.
	"""
	contents = """\
<p>L1</p>
<!--L2-->
<p>L3</p>
<!--L4-->
<p>L5</p>"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (10, 2), (11, 3), (21, 4), (22, 5)]

def test_line_numbers_multiline_comments():
	"""
	Verify line number offset calculations with multiline comments.
	"""
	contents = """\
<!--   L1
   L2 -->
<p>L3</p>
<!--   L4
       L5
	  L6-->
<p>L7</p>
<!--   L8
    L9-->
<p>LA</p>
<!--   LB
    LC-->"""

	s = SourceFile(Path("/"), contents)

	_, bounds = s._sub_with_line_mapping(XML_COMMENT_PATTERN) # pylint: disable=protected-access
	assert bounds == [(0, 1), (1, 3), (11, 4), (12, 7), (22, 8), (23, 10), (33, 11)]
