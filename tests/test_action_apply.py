import logging

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client


def test_apply(tmp_path, caplog, capsys, build_config):
    # arrange
    account_type = models.GoogleDriveAccountTypeOptions.personal
    config_file = tmp_path / "config.json"
    config = build_config(tmp_path, account_type)
    config.save_file(config_file)

    caplog.set_level(logging.DEBUG)

    http_mocks = helpers.FileMoverHttpMockSequence(
        [
            helpers.FileMoverHttpMock(),
        ]
    )
    gd_client = client.GoogleApiClient.get_drive_client(
        config, existing_client=build("drive", "v3", http=http_mocks)
    )

    plan_name = "plan-name"
    plan_file = (config.reports.plans_dir / plan_name).with_suffix(".csv")
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    plan_file.touch(exist_ok=True)

    # act
    exit_code = cli.main(
        ["apply", "--config-file", str(config_file), plan_name], gd_client
    )

    # assert
    assert exit_code == 0

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""
