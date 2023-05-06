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

    api_data = [
        "api-001-personal-folder-level0-files-get.json",
        "api-002-personal-folder-level0-permissions-list.json",
        "api-003-personal-folder-level0-files-list.json",
        "api-004-personal-folder-level1-001-permissions-list.json",
        "api-005-personal-folder-level1-001-files-list.json",
        "api-006-personal-folder-level2-001-permissions-list.json",
        "api-007-personal-folder-level2-001-files-list.json",
        "api-008-personal-file-level3-001-permissions-list.json",
        "api-009-personal-file-level3-002-permissions-list.json",
        "api-010-personal-file-level2-001-permissions-list.json",
        "api-011-personal-file-level2-002-permissions-list.json",
        "api-012-personal-file-level2-003-permissions-list.json",
        "api-013-personal-file-level2-004-permissions-list.json",
        "api-014-personal-file-level1-001-permissions-list.json",
    ]
    http_mocks = helpers.FileMoverHttpMockSequence(
        [helpers.FileMoverHttpMock(f"show/{name}") for name in api_data]
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

    report_entries_file = next(config.reports.entries_dir.iterdir())
    report_entries_csv = csv.DictReader(report_entries_file.read_text().splitlines())
    assert [report.EntryReport(**row).entry_id for row in report_entries_csv] == [
        "personal-folder-level0",
        "personal-folder-level1-001",
        "personal-folder-level2-001",
        "personal-file-level3-001",
        "personal-file-level3-002",
        "personal-file-level2-001",
        "personal-file-level2-002",
        "personal-file-level2-003",
        "personal-file-level2-004",
        "personal-file-level1-001",
    ]

    report_permissions_file = next(config.reports.permissions_dir.iterdir())
    report_permissions_csv = csv.DictReader(
        report_permissions_file.read_text().splitlines()
    )
    assert [
        report.PermissionReport(**row).permission_id for row in report_permissions_csv
    ] == [
        "personal-permission-current-user",
        "personal-permission-current-user",
        "personal-permission-current-user",
        "personal-permission-other-user-1",
        "business-permission-other-user-1",
        "personal-permission-other-user-1",
        "personal-permission-current-user",
        "personal-permission-other-user-2",
        "personal-permission-current-user",
        "personal-permission-other-user-1",
        "personal-permission-current-user",
        "personal-permission-other-user-1",
        "personal-permission-current-user",
        "personal-permission-current-user",
        "personal-permission-other-user-1",
        "personal-permission-other-user-1",
        "personal-permission-current-user",
        "personal-permission-current-user",
    ]

    assert [(lvl, msg) for lg, lvl, msg in caplog.record_tuples] == [
        (20, "file_cache is only supported with oauth2client<4.0.0"),
        (20, "Show entries for PERSONAL account 'personal-user@example.com'."),
        (20, f"Writing entries report '{report_entries_file.name}'."),
        (20, f"Writing permissions report '{report_permissions_file.name}'."),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (20, "Processing folder 'Folder Top' (id personal-folder-level0) props ''."),
        (20, "Starting folder is 'Folder Top'."),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: drive.files.list'.",
        ),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing folder 'Entry Level 1 - Folder 1' (id "
            "personal-folder-level1-001) props ''.",
        ),
        (
            10,
            "Processing page 1 with 5 items from '[HttpRequest] GET: drive.files.list'.",
        ),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing folder 'Entry Level 2 - Folder 1' (id "
            "personal-folder-level2-001) props ''.",
        ),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: drive.files.list'.",
        ),
        (
            10,
            "Processing page 1 with 3 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 3 - File 1' (id personal-file-level3-001) "
            "props ''.",
        ),
        (
            10,
            "Processing page 1 with 3 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 3 - File 2' (id personal-file-level3-002) "
            "props ''.",
        ),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 2 - File 1.docx' (id personal-file-level2-001) "
            "props ''.",
        ),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Copy of Entry Level 2 - File 1.docx' (id "
            "personal-file-level2-002) props ''.",
        ),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 2 - File 3' (id personal-file-level2-003) "
            "props 'CustomFileMoverCopyFileId=personal-file-level2-004'.",
        ),
        (
            10,
            "Processing page 1 with 2 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 2 - File 4' (id personal-file-level2-004) "
            "props 'CustomFileMoverOriginalFileId=personal-file-level2-003'.",
        ),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 1 - File 1' (id personal-file-level1-001) "
            "props ''.",
        ),
        (20, "Processed total of 10 entries."),
        (20, "Finished."),
    ]
