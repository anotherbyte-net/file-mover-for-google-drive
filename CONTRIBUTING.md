# File Mover for Google Drive contributing guide

## Development

Create a virtual environment:

```bash
python -m venv .venv
```

Install runtime dependencies and development dependencies:

```bash
# Windows
.venv\Scripts\activate.ps1

# Linux
source .venv/bin/activate

# install dependencies
python -m pip install --upgrade pip setuptools wheel
python -m pip install --upgrade -r requirements-dev.txt -r requirements.txt

# check for outdated packages
pip list --outdated
```

## Run tests and linters

Run the tests and linters with multiple python versions using tox.

If the pip dependencies have changed, it might be necessary to
(un)comment `recreate = true` in the tox section in `pyproject.toml`.

To run using all available python versions:

```bash
python -X dev -m tox
```

To run using the active python:

```bash
python -X dev -m tox -e py
```

## Generate docs

Generate the docs using pdoc:

```bash
pdoc --docformat google \
  --edit-url file_mover_for_google_drive=https://github.com/anotherbyte-net/file-mover-for-google-drive/blob/main/src/file_mover_for_google_drive/ \
  --search --show-source \
  --output-directory docs \
  ./src/file_mover_for_google_drive
```

## Create and upload release

Generate the distribution package archives.

```bash
python -X dev -m build
```

Upload archives to Test PyPI first.

```bash
python -X dev -m twine upload --repository testpypi dist/*
```

When uploading:

- for username, use `__token__`
- for password, create a token at https://test.pypi.org/manage/account/#api-tokens

Go to the [test project page](https://test.pypi.org/project/file_mover_for_google_drive) and check that it looks ok.

Then create a new virtual environment, install the dependencies, and install from Test PyPI.

```bash
python -m venv .venv-test
source .venv-test/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --upgrade -r requirements.txt

FILE_MOVER_FOR_GOOGLE_DRIVE_VERSION='0.0.1'
pip install --index-url https://test.pypi.org/simple/ --no-deps file-mover-for-google-drive==$FILE_MOVER_FOR_GOOGLE_DRIVE_VERSION
# or
pip install dist/file_mover_for_google_drive-$FILE_MOVER_FOR_GOOGLE_DRIVE_VERSION-py3-none-any.whl
```

Test the installed package.

```bash
file-mover-for-google-drive --version
file-mover-for-google-drive --help
file-mover-for-google-drive show personal
```

If the package seems to work as expected, upload it to the live PyPI.

```bash
python -X dev -m twine upload dist/*
```

When uploading:

- for username, use `__token__`
- for password, create a token at https://pypi.org/manage/account/#api-tokens

Go to the [live project page](https://pypi.org/project/file-mover-for-google-drive) and check that it looks ok.

Done!
