import csv
import logging

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client, report


def test_show(tmp_path, caplog, capsys, build_config):
    # arrange
    account_type = models.GoogleDriveAccountTypeOptions.PERSONAL
    config_file = tmp_path / "config.json"
    config = build_config(tmp_path, account_type)
    config.save_file(config_file)

    caplog.set_level(logging.DEBUG)

    http_mocks = helpers.FileMoverHttpMockSequence(
        [
            helpers.FileMoverHttpMock(
                headers=helpers.FileMoverHttpMock.get_status_bad_request()
            ),
        ]
    )
    gd_client = client.GoogleApiClient.get_drive_client(
        config, existing_client=build("drive", "v3", http=http_mocks)
    )

    # act
    exit_code = cli.main(["show", "--config-file", str(config_file)], gd_client)

    # assert
    assert exit_code == 0

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""

    report_entries_file = next(config.report_entries_dir.iterdir())
    report_entries_csv = csv.DictReader(report_entries_file.read_text().splitlines())
    assert [report.EntryReport(**row).entry_id for row in report_entries_csv] == [
        "personal-top-folder",
        "folder_1_a",
        "file_1_a",
        "folder_2_a",
        "file_2_a",
        "file_2_b",
        "file_2_c",
        "folder_3_a",
        "file_3_a_a",
        "file_2_a_b",
        "folder_3_b",
        "file_3_b_a",
        "file_3_b_b",
    ]

    report_permissions_file = next(config.report_permissions_dir.iterdir())
    report_permissions_csv = csv.DictReader(
        report_permissions_file.read_text().splitlines()
    )
    assert [
        report.PermissionReport(**row).permission_id for row in report_permissions_csv
    ] == [
        "personal-top-folder-owner",
        "personal-top-folder-other1",
        "folder_1_a-writer",
        "folder_1_a-other-user1-owner",
        "folder_1_a-other-user2-reader",
        "file_1_a-owner",
        "folder_2_a-owner",
        "file_2_a-owner",
        "file_2_b-owner",
        "file_2_c-owner",
        "folder_3_a-owner",
        "file_3_a_a-owner",
        "file_2_a_b-owner",
        "folder_3_b-owner",
        "file_3_b_a-owner",
        "file_3_b_b-reader",
        "file_3_b_b-owner",
    ]

    assert [(lvl, msg) for lg, lvl, msg in caplog.record_tuples] == [
        (20, "Show entries for 'My Drive' in user 'personal-user@example.com'."),
        (20, "Starting with folder 'personal-top-folder'."),
        (20, f"Writing entries report '{report_entries_file.name}'."),
        (20, f"Writing permissions report '{report_permissions_file.name}'."),
        (20, "Starting."),
        (20, "Starting folder is 'Name for personal-top-folder'."),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (20, "Processed 10 entries."),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (20, "Processed total of 13 entries."),
        (20, "Finished."),
    ]
