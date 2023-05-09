import sys

import pytest

from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import utils

expected_version = "0.0.1"


@pytest.mark.parametrize("main_args,exit_code", [([], 1), (["--help"], 0)])
def test_cli_no_args(capsys, caplog, main_args, exit_code, equal_ignore_whitespace):
    with pytest.raises(SystemExit, match=str(exit_code)):
        cli.main(main_args)

    prog_help = """usage: file-mover-for-google-drive [-h] [--version] {show,plan,apply,tidy-properties} ...

Helps move files between Google Drive accounts.

positional arguments:
  {show,plan,apply,tidy-properties}  sub-command help
    show                             Show the files, folders, and permissions in a Google
                                     Drive.
    plan                             Build a plan of the changes.
    apply                            Apply changes from a plan file.
    tidy-properties                  Tidy entry properties.

options:
  -h, --help         show this help message and exit
  --version          show program's version number and exit"""

    stdout, stderr = capsys.readouterr()
    if main_args == ["--help"]:
        equal_ignore_whitespace(stdout, prog_help)
        assert stderr == ""
        assert caplog.record_tuples == []

    if not main_args:
        assert stdout == ""
        equal_ignore_whitespace(stderr, prog_help)
        assert caplog.record_tuples == []


def test_cli_version(capsys, caplog):
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--version"])

    stdout, stderr = capsys.readouterr()
    assert stdout == f"{utils.get_name_dash()} {expected_version}\n"
    assert stderr == ""
    assert caplog.record_tuples == []
