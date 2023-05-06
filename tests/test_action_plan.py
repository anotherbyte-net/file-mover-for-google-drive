import csv
import dataclasses
import logging

from googleapiclient.discovery import build

import helpers
from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import models, client, report


def test_plan(tmp_path, caplog, capsys, build_config):
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
        "api-008-personal-folder-level2-001-files-list.json",
        "api-009-personal-file-level3-001-permissions-list.json",
        "api-010-personal-file-level3-002-permissions-list.json",
        "api-011-personal-file-level3-002-files-list.json",
        "api-012-personal-file-level2-001-permissions-list.json",
        "api-013-personal-file-level2-002-permissions-list.json",
        "api-014-personal-file-level2-003-permissions-list.json",
        "api-015-personal-file-level2-004-files-get.json",
        "api-016-personal-file-level2-004-permissions-list.json",
        "api-016-personal-file-level2-004-permissions-list.json",
        "api-017-personal-file-level1-001-permissions-list.json",
    ]
    http_mocks = helpers.FileMoverHttpMockSequence(
        [helpers.FileMoverHttpMock(f"plan/{name}") for name in api_data]
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
        "personal-permission-anyone",
        "personal-permission-current-user",
        "personal-permission-other-user-1",
        "personal-permission-other-user-1",
        "personal-permission-current-user",
        "personal-permission-current-user",
    ]

    report_plans_file = next(config.reports.plans_dir.iterdir())
    report_plans_csv = csv.DictReader(report_plans_file.read_text().splitlines())
    assert [
        {k: v for k, v in dataclasses.asdict(report.PlanReport(**row)).items() if v}
        for row in report_plans_csv
    ] == [
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "description": "create an owned folder with same name",
            "drive_id": "My Drive",
            "end_entry_name": "Entry Level 2 - Folder 1",
            "end_entry_path": "Folder Top/Entry Level 1 - Folder 1",
            "end_user_access": "owner",
            "end_user_email": "personal-current-user@example.com",
            "end_user_name": "personal-current-user",
            "entry_id": "personal-folder-level2-001",
            "item_action": "create-folder",
            "item_type": "folder",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 1",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "owner",
            "begin_user_email": "personal-current-user@example.com",
            "begin_user_name": "personal-current-user",
            "description": "move an entry from an unowned folder to an owned folder",
            "drive_id": "My Drive",
            "end_entry_name": "Entry Level 3 - File 1",
            "end_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "end_user_access": "owner",
            "end_user_email": "personal-current-user@example.com",
            "end_user_name": "personal-current-user",
            "entry_id": "personal-file-level3-001",
            "item_action": "move-entry",
            "item_type": "file",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 1",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "writer",
            "begin_user_email": "business-other-user-1@example.com",
            "begin_user_name": "business-other-user-1",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level3-001",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "business-permission-other-user-1",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 1",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "writer",
            "begin_user_email": "personal-other-user-1@example.com",
            "begin_user_name": "personal-other-user-1",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level3-001",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "personal-permission-other-user-1",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 2",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "owner",
            "begin_user_email": "personal-other-user-1@example.com",
            "begin_user_name": "personal-other-user-1",
            "description": "copy file to create a new file owned by the current user",
            "drive_id": "My Drive",
            "end_entry_name": "Entry Level 3 - File 2",
            "end_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "end_user_access": "owner",
            "end_user_email": "personal-current-user@example.com",
            "end_user_name": "personal-current-user",
            "entry_id": "personal-file-level3-002",
            "item_action": "copy-file",
            "item_type": "file",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 2",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "owner",
            "begin_user_email": "personal-current-user@example.com",
            "begin_user_name": "personal-current-user",
            "description": "move an entry from an unowned folder to an owned folder",
            "drive_id": "My Drive",
            "end_entry_name": "Entry Level 3 - File 2",
            "end_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "end_user_access": "owner",
            "end_user_email": "personal-current-user@example.com",
            "end_user_name": "personal-current-user",
            "entry_id": "personal-file-level3-002",
            "item_action": "move-entry",
            "item_type": "file",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 3 - File 2",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1/Entry Level 2 - "
            "Folder 1",
            "begin_user_access": "writer",
            "begin_user_email": "personal-other-user-2@example.com",
            "begin_user_name": "personal-other-user-2",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level3-002",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "personal-permission-other-user-2",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Copy of Entry Level 2 - File 1.docx",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1",
            "begin_user_access": "writer",
            "begin_user_email": "personal-other-user-1@example.com",
            "begin_user_name": "personal-other-user-1",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level2-002",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "personal-permission-other-user-1",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Copy of Entry Level 2 - File 1.docx",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1",
            "begin_user_access": "reader",
            "begin_user_name": "personal-anyone",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level2-002",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "personal-permission-anyone",
        },
        {
            "account_id": "personal-current-user@example.com",
            "account_type": "personal",
            "begin_entry_name": "Entry Level 2 - File 4",
            "begin_entry_path": "Folder Top/Entry Level 1 - Folder 1",
            "begin_user_access": "writer",
            "begin_user_email": "personal-other-user-1@example.com",
            "begin_user_name": "personal-other-user-1",
            "description": "delete permission for non-owner and not current user",
            "drive_id": "My Drive",
            "entry_id": "personal-file-level2-004",
            "item_action": "delete-permission",
            "item_type": "file",
            "permission_id": "personal-permission-other-user-1",
        },
    ]

    assert [(lvl, msg) for lg, lvl, msg in caplog.record_tuples] == [
        (20, "file_cache is only supported with oauth2client<4.0.0"),
        (
            20,
            "Plan modifications for PERSONAL account "
            "'personal-current-user@example.com'.",
        ),
        (20, f"Writing entries report '{report_entries_file.name}'."),
        (20, f"Writing permissions report '{report_permissions_file.name}'."),
        (20, f"Writing plans report '{report_plans_file.name}'."),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (20, "Processing folder 'Folder Top' (id personal-folder-level0) props ''."),
        (10, "Will not change the top-level folder 'Folder Top'."),
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
        (10, "Will never copy an owned file or folder."),
        (10, "Will never move files and folders in an owned folder."),
        (10, "Will never rename folders."),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
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
            "Processing page 1 with 0 items from '[HttpRequest] GET: drive.files.list'.",
        ),
        (
            20,
            "Added plan create-folder folder 'Entry Level 2 - Folder 1' path 'Folder "
            "Top/Entry Level 1 - Folder 1' user 'personal-current-user' email "
            "'personal-current-user@example.com' access 'owner'.",
        ),
        (10, "Will never move files and folders in an owned folder."),
        (10, "Will never rename folders."),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(EDITOR).",
        ),
        (
            10,
            "Keep permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(OWNER).",
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
        (10, "Will never copy an owned file or folder."),
        (
            20,
            "Added plan move-entry file 'Entry Level 3 - File 1' path 'Folder Top/Entry "
            "Level 1 - Folder 1/Entry Level 2 - Folder 1' user 'personal-current-user' "
            "email 'personal-current-user@example.com' access 'owner'.",
        ),
        (10, "No change to file name."),
        (
            10,
            "Delete permission business-other-user-1 <business-other-user-1@example.com> "
            "(EDITOR).",
        ),
        (
            20,
            "Added plan delete-permission file 'Entry Level 3 - File 1' path 'Folder "
            "Top/Entry Level 1 - Folder 1/Entry Level 2 - Folder 1' user "
            "'business-other-user-1' email 'business-other-user-1@example.com' access "
            "'writer'.",
        ),
        (
            10,
            "Delete permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(EDITOR).",
        ),
        (
            20,
            "Added plan delete-permission file 'Entry Level 3 - File 1' path 'Folder "
            "Top/Entry Level 1 - Folder 1/Entry Level 2 - Folder 1' user "
            "'personal-other-user-1' email 'personal-other-user-1@example.com' access "
            "'writer'.",
        ),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
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
            "Processing page 1 with 0 items from '[HttpRequest] GET: drive.files.list'.",
        ),
        (
            20,
            "Added plan copy-file file 'Entry Level 3 - File 2' path 'Folder Top/Entry "
            "Level 1 - Folder 1/Entry Level 2 - Folder 1' user 'personal-other-user-1' "
            "email 'personal-other-user-1@example.com' access 'owner'.",
        ),
        (
            20,
            "Added plan move-entry file 'Entry Level 3 - File 2' path 'Folder Top/Entry "
            "Level 1 - Folder 1/Entry Level 2 - Folder 1' user 'personal-current-user' "
            "email 'personal-current-user@example.com' access 'owner'.",
        ),
        (10, "No change to file name."),
        (
            10,
            "Delete permission personal-other-user-2 <personal-other-user-2@example.com> "
            "(EDITOR).",
        ),
        (
            20,
            "Added plan delete-permission file 'Entry Level 3 - File 2' path 'Folder "
            "Top/Entry Level 1 - Folder 1/Entry Level 2 - Folder 1' user "
            "'personal-other-user-2' email 'personal-other-user-2@example.com' access "
            "'writer'.",
        ),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(EDITOR).",
        ),
        (
            10,
            "Keep permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(OWNER).",
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
        (10, "Will never copy an owned file or folder."),
        (10, "Will never move files and folders in an owned folder."),
        (10, "No change to file name."),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
        ),
        (
            10,
            "Processing page 1 with 3 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Copy of Entry Level 2 - File 1.docx' (id "
            "personal-file-level2-002) props ''.",
        ),
        (10, "Will never copy an owned file or folder."),
        (10, "Will never move files and folders in an owned folder."),
        (
            10,
            "Config prevented renaming 'Copy of Entry Level 2 - File 1.docx' to 'Entry "
            "Level 2 - File 1.docx'.",
        ),
        (
            10,
            "Delete permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(EDITOR).",
        ),
        (
            20,
            "Added plan delete-permission file 'Copy of Entry Level 2 - File 1.docx' "
            "path 'Folder Top/Entry Level 1 - Folder 1' user 'personal-other-user-1' "
            "email 'personal-other-user-1@example.com' access 'writer'.",
        ),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
        ),
        (10, "Delete permission anyone with link (VIEWER)."),
        (
            20,
            "Added plan delete-permission file 'Copy of Entry Level 2 - File 1.docx' "
            "path 'Folder Top/Entry Level 1 - Folder 1' user 'personal-anyone' access "
            "'reader'.",
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
            10,
            "Found existing copy of file 'Entry Level 2 - File 3' at 'Folder Top/Entry "
            "Level 1 - Folder 1'.",
        ),
        (10, "Will never move files and folders in an owned folder."),
        (10, "No change to file name."),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(EDITOR).",
        ),
        (
            10,
            "Keep permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(OWNER).",
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
        (10, "Will never copy an owned file or folder."),
        (10, "Will never move files and folders in an owned folder."),
        (10, "No change to file name."),
        (
            10,
            "Delete permission personal-other-user-1 <personal-other-user-1@example.com> "
            "(EDITOR).",
        ),
        (
            20,
            "Added plan delete-permission file 'Entry Level 2 - File 4' path 'Folder "
            "Top/Entry Level 1 - Folder 1' user 'personal-other-user-1' email "
            "'personal-other-user-1@example.com' access 'writer'.",
        ),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
        ),
        (
            10,
            "Processing page 1 with 1 items from '[HttpRequest] GET: "
            "drive.permissions.list'.",
        ),
        (
            20,
            "Processing file 'Entry Level 1 - File 1.pdf' (id personal-file-level1-001) "
            "props ''.",
        ),
        (10, "Will never copy an owned file or folder."),
        (10, "Will never move files and folders in an owned folder."),
        (10, "No change to file name."),
        (
            10,
            "Keep permission personal-current-user <personal-current-user@example.com> "
            "(OWNER).",
        ),
        (20, "Processed total of 10 entries."),
        (20, "Finished."),
    ]
