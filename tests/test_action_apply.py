import csv
import dataclasses
import logging
import shutil
from importlib import resources

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client, report


def test_apply(tmp_path, caplog, capsys, build_config):
    # arrange
    account_type = models.GoogleDriveAccountTypeOptions.PERSONAL
    config_file = tmp_path / "config.json"
    config = build_config(tmp_path, account_type)
    config.save_file(config_file)

    caplog.set_level(logging.DEBUG)

    api_data = []
    http_mocks = helpers.FileMoverHttpMockSequence(
        [helpers.FileMoverHttpMock(f"apply/{name}") for name in api_data]
    )
    gd_client = client.GoogleApiClient.get_drive_client(
        config, existing_client=build("drive", "v3", http=http_mocks)
    )

    plan_name = "plan-for-apply"
    with resources.as_file(
        resources.files("resources").joinpath(f"apply/{plan_name}.csv")
    ) as file_path:
        plan_source_file = file_path.absolute()

    plan_file = (config.reports.plans_dir / plan_name).with_suffix(".csv")
    plan_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(str(plan_source_file), str(plan_file))

    # act
    exit_code = cli.main(
        ["apply", "--config-file", str(config_file), plan_name], gd_client
    )

    # assert
    assert exit_code == 0

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""

    report_plans_csv = csv.DictReader(plan_file.read_text().splitlines())
    assert [
        {k: v for k, v in dataclasses.asdict(report.PlanReport(**row)).items() if v}
        for row in report_plans_csv
    ] == []

    report_outcomes_file = next(config.reports.outcomes_dir.iterdir())
    report_outcomes_csv = csv.DictReader(report_outcomes_file.read_text().splitlines())
    assert [
        dataclasses.asdict(report.OutcomeReport(**row)) for row in report_outcomes_csv
    ] == []

    assert [(lvl, msg) for lg, lvl, msg in caplog.record_tuples] == [
        (20, "file_cache is only supported with oauth2client<4.0.0"),
        (
            20,
            "Apply modifications for PERSONAL account "
            "'personal-current-user@example.com'.",
        ),
        (20, "Reading plans report 'plan-for-apply'."),
        (20, f"Writing outcomes report '{report_outcomes_file.name}'."),
        (20, "Processed total of 0 entries."),
        (20, "Finished."),
    ]
