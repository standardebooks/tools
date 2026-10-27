"""
Test UTF-8 validation across file-reading commands.
"""

from pathlib import Path
import shutil
import sys

import pytest

import se
from se.main import main
from se.se_epub import SeEpub


@pytest.mark.parametrize("binary", [False, True])
@pytest.mark.parametrize("contents", [b"ASCII", "Café 日本語".encode("utf-8"), b"\xef\xbb\xbf<p>Text</p>"])
def test_read_utf8_valid(tmp_path: Path, binary: bool, contents: bytes) -> None:
	"""
	Accept valid UTF-8 without changing the returned text or bytes.
	"""

	filename = tmp_path / "input.xhtml"
	filename.write_bytes(contents)
	if binary:
		with open(filename, "rb") as file:
			assert se.read_utf8(file) == contents
	else:
		with open(filename, "r", encoding="utf-8") as file:
			assert se.read_utf8(file) == contents.decode("utf-8")


@pytest.mark.parametrize("arguments, suffix", [
	(["split-file"], ".xhtml"),
	(["word-count"], ".xhtml"),
	(["clean"], ".xhtml"),
	(["clean"], ".css"),
	(["typogrify"], ".xhtml"),
	(["semanticate"], ".xhtml"),
	(["modernize-spelling"], ".xhtml"),
	(["british2american"], ".xhtml"),
	(["hyphenate"], ".xhtml"),
	(["find-mismatched-dashes"], ".xhtml"),
	(["find-mismatched-diacritics"], ".xhtml"),
	(["find-unusual-characters"], ".xhtml"),
	(["build-title"], ".xhtml"),
	(["css-select", "p"], ".xhtml"),
	(["xpath", "//p"], ".xhtml"),
])
@pytest.mark.parametrize("invalid_bytes", [b"\xe9", b"\xc3", b"\xc0\xaf", b"\xed\xa0\x80"])
def test_commands_reject_invalid_utf8(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], arguments: list[str], suffix: str, invalid_bytes: bytes) -> None:
	"""
	Reject invalid UTF-8 with the encoding error code before modifying the input.
	"""

	filename = tmp_path / f"input{suffix}"
	contents = b"<p>" + b"a" * 10000 + invalid_bytes + b"</p>"
	filename.write_bytes(contents)
	monkeypatch.chdir(tmp_path)
	monkeypatch.setattr(sys, "argv", ["se", "--plain", *arguments, str(filename)])
	with pytest.raises(SystemExit) as error:
		main()
	assert error.value.code == se.InvalidEncodingException.code
	assert "File is not UTF-8:" in capsys.readouterr().err
	assert filename.read_bytes() == contents
	assert not list(tmp_path.glob("chapter-*.xhtml"))


@pytest.mark.parametrize("method", ["get_file", "get_dom"])
def test_ebook_reads_reject_invalid_utf8(tmp_path: Path, testbook__directory: Path, method: str) -> None:
	"""
	Preserve encoding errors when reading ebook text or parsing ebook XML.
	"""

	ebook = SeEpub(testbook__directory)
	filename = tmp_path / "invalid.xhtml"
	filename.write_bytes(b'<html encoding="iso-8859-1"><p>caf\xe9</p></html>')
	with pytest.raises(se.InvalidEncodingException, match="File is not UTF-8:"):
		getattr(ebook, method)(filename)


def test_split_file_rejects_invalid_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
	"""
	Validate the template before writing any split files.
	"""

	filename = tmp_path / "input.xhtml"
	filename.write_text("<p>Café</p><!--se:split--><p>Two</p>", encoding="utf-8")
	template = tmp_path / "template.xhtml"
	template.write_bytes(b"<html>caf\xe9TEXT</html>")
	monkeypatch.chdir(tmp_path)
	monkeypatch.setattr(sys, "argv", ["se", "--plain", "split-file", "--template-file", str(template), str(filename)])
	with pytest.raises(SystemExit) as error:
		main()
	assert error.value.code == se.InvalidEncodingException.code
	assert str(template) in capsys.readouterr().err
	assert not list(tmp_path.glob("chapter-*.xhtml"))


@pytest.mark.parametrize("relative_path", ["src/META-INF/container.xml", "src/epub/content.opf", "src/epub/text/chapter-1.xhtml"])
def test_ebook_command_preserves_encoding_errors(tmp_path: Path, testbook__directory: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], relative_path: str) -> None:
	"""
	Report encoding errors from ebook initialization and chapter processing consistently.
	"""

	ebook_path = tmp_path / "ebook"
	shutil.copytree(testbook__directory, ebook_path)
	filename = ebook_path / relative_path
	filename.write_bytes(filename.read_bytes() + b"\xff")
	monkeypatch.setattr(sys, "argv", ["se", "--plain", "build-toc", "--stdout", str(ebook_path)])
	with pytest.raises(SystemExit) as error:
		main()
	assert error.value.code == se.InvalidEncodingException.code
	assert "File is not UTF-8:" in capsys.readouterr().err
