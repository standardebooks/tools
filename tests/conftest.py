"""
Customization functions for pytest.
"""

import os
import shutil
from pathlib import Path
from typing import Generator, TYPE_CHECKING

import pytest

if TYPE_CHECKING:
	from _pytest.config import Config

pytest.register_assert_rewrite("helpers")

def pytest_addoption(parser: pytest.Parser):
	"""
	Additional pytest command-line options.
	"""
	parser.addoption("--lint-subset", action="store", dest="lint_subset", choices=("css","filesystem","metadata","semantics","typography","typos","xhtml"),  help="Specify a subset of lint tests to be performed")
	parser.addoption("--save-golden-files", action="store_true", default=False, help="Save updated versions of all golden output files")
	parser.addoption("--save-new-draft", action="store_true", default=False, help="Update draft ebook used as base for ebookcmd tests")

@pytest.fixture(name="draftbook__name", scope="session")
def fixture_draftbook__name():
	"""
	Return name of draft book.
	"""
	return "jane-austen_draft-novel"

@pytest.fixture(name="testbook__name", scope="session")
def fixture_testbook__name():
	"""
	Return name of test book.
	"""
	return "jane-austen_test-novel"

@pytest.fixture(scope="session")
def draftbook__directory(tmp_path_factory: pytest.TempPathFactory, draftbook__name: str) -> Generator[Path, None, None]:
	"""
	Return the Path object for a temporary copy of the draft book content.
	"""
	base_directory = Path(__file__).parent / "data" / "draftbook"
	src_directory = base_directory / draftbook__name
	dest_directory = tmp_path_factory.getbasetemp() / "draftbook"
	shutil.copytree(src_directory, dest_directory)
	yield dest_directory

@pytest.fixture(scope="session")
def testbook__directory(tmp_path_factory: pytest.TempPathFactory, testbook__name: str) -> Generator[Path, None, None]:
	"""
	Return the Path object for a temporary copy of the test book content.
	"""
	base_directory = Path(__file__).parent / "data" / "testbook"
	src_directory = base_directory / testbook__name
	dest_directory = tmp_path_factory.getbasetemp() / "testbook"
	shutil.copytree(src_directory, dest_directory)
	yield dest_directory

@pytest.fixture
def work__directory(tmp_path: Path) -> Generator[Path, None, None]:
	"""Return the Path object for a temporary working directory. The current working
	directory is updated to this temporary directory until the test returns.
	"""
	old_working_directory = os.getcwd()
	os.chdir(tmp_path)
	yield tmp_path
	os.chdir(old_working_directory)

@pytest.fixture(scope="session")
def update_golden(pytestconfig: 'Config') -> bool:
	"""
	Save updated versions of all golden output files when this flag is True.
	"""
	return pytestconfig.getoption("--save-golden-files")
