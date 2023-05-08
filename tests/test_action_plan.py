import logging

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client, report


def test_plan_before(tmp_path, caplog, capsys, build_config):
    # arrange
    resource_dir = "plan-before"

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

    # act
    exit_code = cli.main(["plan", "--config-file", str(config_file)], gd_client)

    # assert
    assert exit_code == 0

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""

    assert len(http_mocks.request_sequence) == len(api_data)

    # check outputs
    output_items = [
        {
            "report_class": report.EntryReport,
            "actual_path": config.reports.entries_dir,
            "expected_path": f"{resource_dir}/entries.csv",
        },
        {
            "report_class": report.PermissionReport,
            "actual_path": config.reports.permissions_dir,
            "expected_path": f"{resource_dir}/permissions.csv",
        },
        {
            "report_class": report.PlanReport,
            "actual_path": config.reports.plans_dir,
            "expected_path": f"{resource_dir}/plans.csv",
        },
    ]
    actual_report_paths = helpers.check_reports(output_items)

    helpers.compare_logs(caplog.record_tuples, resource_dir, actual_report_paths)


def test_plan_after(tmp_path, caplog, capsys, build_config):
    # arrange
    resource_dir = "plan-after"

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

    # act
    exit_code = cli.main(["plan", "--config-file", str(config_file)], gd_client)

    # assert
    assert exit_code == 0

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""

    assert len(http_mocks.request_sequence) == len(api_data)

    # check outputs
    output_items = [
        {
            "report_class": report.EntryReport,
            "actual_path": config.reports.entries_dir,
            "expected_path": f"{resource_dir}/entries.csv",
        },
        {
            "report_class": report.PermissionReport,
            "actual_path": config.reports.permissions_dir,
            "expected_path": f"{resource_dir}/permissions.csv",
        },
        {
            "report_class": report.PlanReport,
            "actual_path": config.reports.plans_dir,
            "expected_path": f"{resource_dir}/plans.csv",
        },
    ]
    actual_report_paths = helpers.check_reports(output_items)

    helpers.compare_logs(caplog.record_tuples, resource_dir, actual_report_paths)
