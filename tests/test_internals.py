"""
Test internal SE programming functions
"""

from se.se_epub_generate_toc import add_landmark
import se.easy_xml

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
