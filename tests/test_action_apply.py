import logging
import shutil

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client, report


def test_apply_before(tmp_path, caplog, capsys, build_config):
    # arrange
    resource_dir = "apply-before"

    account_type = models.GoogleDriveAccountTypeOptions.PERSONAL
    config_file = tmp_path / "config.json"
    config = build_config(tmp_path, account_type)
    config.save_file(config_file)

    caplog.set_level(logging.DEBUG)

    api_data = helpers.api_json_files(resource_dir)
    http_mocks = helpers.FileMoverHttpMockSequence(
        [helpers.FileMoverHttpMock(file) for file in api_data]
    )

    gd_client = client.GoogleApiClient.get_drive_client(
        config, existing_client=build("drive", "v3", http=http_mocks)
    )

    plan_name = "plans"
    plan_source_file = helpers.get_resource_path(f"plan-before/{plan_name}.csv")

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

    assert len(http_mocks.request_sequence) == len(api_data)

    output_items = [
        {
            "report_class": report.OutcomeReport,
            "actual_path": config.reports.outcomes_dir,
            "expected_path": f"{resource_dir}/outcomes.csv",
        },
    ]
    actual_report_paths = helpers.check_reports(output_items)

    helpers.compare_logs(caplog.record_tuples, resource_dir, actual_report_paths)


def test_apply_after(tmp_path, caplog, capsys, build_config):
    # arrange
    resource_dir = "apply-after"

    account_type = models.GoogleDriveAccountTypeOptions.PERSONAL
    config_file = tmp_path / "config.json"
    config = build_config(tmp_path, account_type)
    config.save_file(config_file)

    caplog.set_level(logging.DEBUG)

    api_data = helpers.api_json_files(resource_dir)
    http_mocks = helpers.FileMoverHttpMockSequence(
        [helpers.FileMoverHttpMock(file) for file in api_data]
    )

    gd_client = client.GoogleApiClient.get_drive_client(
        config, existing_client=build("drive", "v3", http=http_mocks)
    )

    plan_name = "plans"
    plan_source_file = helpers.get_resource_path(f"plan-before/{plan_name}.csv")

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

    assert len(http_mocks.request_sequence) == len(api_data)

    output_items = [
        {
            "report_class": report.OutcomeReport,
            "actual_path": config.reports.outcomes_dir,
            "expected_path": f"{resource_dir}/outcomes.csv",
        },
    ]
    actual_report_paths = helpers.check_reports(output_items)

    helpers.compare_logs(caplog.record_tuples, resource_dir, actual_report_paths)
