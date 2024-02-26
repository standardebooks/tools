# Testing with `pytest`

Similar to `pylint`, the `pytest` command can be injected into the venv `pipx` created for the `standardebooks` package:

```shell
pipx inject standardebooks pytest==7.3.1
```

The tests are executed by calling `pytest` from the top level or your tools repo:

```shell
cd /path/to/tools/repo
$HOME/.local/pipx/venvs/standardebooks/bin/pytest
```

## Test structure

Testing is structured such that, for most testing, all that is needed to implement a new test is to create a directory structure and a set of input files.

Tests are located in the `tests` subdirectory of the `tools` top-level directory. The various `se` commands have been divided into modules based on what they take as input and deliver as output. There is a module code file (`test_{module}.py`) and a directory for each module. Each module code file contains documentation that lists the `se` commands that are included in that module. The modules are:

1. `draft_commands`—These take a draft (i.e. incomplete) SE ebook directory structure as input, combined with the file(s) provided for the test, and update one or more of the ebook files in some way. Each command has its own subdirectory, and each test for the command is in a subdirectory beneath that one. The tests are named test-X, e.g. test-1, test-2, test-13, etc.
2. `ebook_commands`—These take a feature-complete SE ebook directory structure as input, combined with the file(s) provided for the test, and update one or more of the files (or, in the case of `build`, produce ebook file(s)). The test directory structure is the same as for draft_commands.
3. `file_commands`—These take one or more file(s) as input, or in the case of create-draft, nothing, and produce files (possibly in a directory tree) as output. The test directory structure is the same as for draft_commands.
4. `stdout_commands`—These take a draft (i.e. incomplete) SE ebook directory structure as input, combined with the file(s) provided for the test, and output text to stdout. The test directory structure is the same as for draft_commands.
5. `lint`—`se`’s lint command takes a feature-complete ebook directory structure as input, and writes any errors found in the ebook to stdout. There is a separate directory for each type of lint error, e.g. css, filesystem, metadata, etc., each of which contains the test directories for the errors of that type. The test directories are named for the specific lint error being tested, e.g. `c-003`, `x-015`, etc. Each error has a single test, and therefore a single directory.
6. `string_commands`—These take a string as input and output a string to stdout. Since they do not take file input, all tests are contained in a single file, contained in a directory named for the command being tested. The file contains one line per test.
7. In addition, there is a `data` directory that contains two SE ebook structures beneath it, one for a draft ebook (created via `se create-draft`), and one for a feature-complete test ebook, i.e. it will build without error and generates no lint errors.

## Creating a test
For the first four modules above (draft, ebook, file, stdout), creating a test involves these steps.

1. If the subdirectory for the command being tested does not exist below the module directory, create it.
2. Create a subdirectory beneath the command directory labeled `test-X`, where X is the next test number in sequence. For example, if `test-1` through `test-5` already exists, then create a `test-6` directory.
3. Within that new test directory, create `golden` and `in` subdirectories.
4. Within the `in` directory, create the minimum SE ebook directory tree needed for the files being used in the test. For example, if only a chapter file is needed for the test, then create an `src/epub/text` directory structure. If a css file is needed for the test, create a `src/epub/css` directory structure.
5. Copy/create the files needed for the test into that directory structure, putting the files in their appropriate directory.
6. If no arguments are needed for the command being tested, that is all that is needed in the `in` directory. However, if arguments to the `se` command are needed for the test, then a file named `{command}-command`, e.g. `build-manifest-command` should be created in the test directory. That file should contain a single line, with the command name and arguments on it. Thus, to test that the standard out argument to the `build-manifest` command is working, create a `build-manifest-command` file in the test-X directory and populate it with a line containing `build-manifest --stdout`.
7. Run the test with the `--save-golden-files` option to create a valid “golden” file, i.e. the file that future tests will be compared against. See Running tests below for how to run a single test.

For lint, the steps are almost the same, with the exception of the top-level test directory.
1. Beneath the appropriate lint subtype directory, create a directory for the lint error id being tested. For example, c-XXX errors are beneath the `css` directory, m-XXX errors beneath the `metadata` directory, etc. Note that unlike the above modules, there should only be a single test for each lint error id. If additional conditions need to be tested for a lint error, the existing input file(s) should be updated to include the additional conditions.
2. Continue the above steps, beginning with step #3.
3. A lint test should be thorough; if the lint error has exceptions, those exceptions should be included as part of the test. If the lint error has multiple matches, each match should be tested. E.g., see the `y-003` test input files.
    In addition, each test should try to restrict the errors generated to just the individual lint error being tested. If that is impossible, please note in the input files that the additional error will be generated for that condition. See again the `y-003` test input files.

For string commands:
1. Each string command already has the appropriate directory structure and a file, with the same name as the command, containing one or more tests.
2. To add additional tests, or modify existing ones, edit the existing command file and add additional lines at the bottom of the file for the additional test(s).
3. Each line in the file consists of two comma-delimited strings: the input to the command, a comma, and the “golden” output from the command.

## Running tests

To run all tests manually, run `pytest tests` from the top-level `tools` directory.
To run a single module's test, include the module file, e.g. `pytest tests/test_stdout_commands.py`.
To run a single test, include the module file basename and the test id in the format `pytest tests/test_{module}.py::test_{module}[{test-id}]`. For example, the third test for `build-spine` would be `pytest tests/test_stdout_commands.py::test_stdout_commands[build-spine-test-3]`.
For lint, the format is `tests_lint.py::test_lint_py[{lint-error-id}]`, e.g. `pytest tests/test_lint.py::test_lint[c-003]`.

To see test ids, run pytest in collect-only mode, e.g. `pytest --collect-only tests` or `pytest --collect-only tests:/test_lint.py`, or pass the -v[v] option when running the tests, e.g. `pytest -v tests`.

The testing directory structure:
```
|__ tests/
|   |__ conftest.py—pytest configuration file
|   |__ helpers.py—pytest helper fixtures, etc.
|   |__ test_draft_commands.py
|   |__ test_ebook_commands.py
|   |__ test_file_commands.py
|   |__ test_internals.py
|   |__ test_lint_commands.py
|   |__ test_stdout_commands.py
|   |__ test_string_commands.py
|
|__ data/
|   |__ draftbook/
|   |   |__ a complete draft ebook structure
|   |
|   |__ testbook/
|   |   |__ a feature-complete test ebook structure
|
|__ draft_commands/
|   |__ british2american/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |__ build-title/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |   |   |__ test-2/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |__ etc.
|
|__ ebook_commands/
|   |__ build/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |__ build-ids/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |__ etc.
|
|__ file_commands/
|   |__ create-draft/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|__ . . .
|   |__ split-file/
|   |   |   |__ test-1/
|   |   |   |   |__ golden/
|   |   |   |   |__ in/
|   |__ etc.
|
|__ lint/
|   |__ css/
|   |   |__ c-001/
|   |   |   |__ golden/
|   |   |   |   |__ c-001-out.txt
|   |   |   |__ in/
|
|   |__ filesystem/
|   |   |__ f-001/
|   |   |   |__ golden/
|   |   |   |   |__ f-001-out.txt
|   |   |   |__ in/
|   |__ etc.
|
|__ stdout_commands/
|   |__ build-manifest/
|   |   |   |__ test-1/
|   |   |   |   |__ in/
|   |   |   |   |__ golden/
|
|   |__ build-spine/
|   |   |   |__ test-1/
|   |   |   |   |__ in/
|   |   |   |   |__ golden/
|   |__ etc.
|
|__ string_commands/
|   |__ dec2roman/
|   |   |__ dec2roman
|   |__ make-url-safe/
|   |   |__ make-url-safe
|   |__ etc.
````