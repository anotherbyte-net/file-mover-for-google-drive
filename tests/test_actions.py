import csv
import dataclasses
import json
import logging
from importlib.resources import files

import pytest

from file_mover_for_google_drive import cli
from file_mover_for_google_drive.common import client, report


def test_show(tmp_path, caplog, capsys, build_config):
    # arrange
    config_file = tmp_path / "config.json"
    config = build_config
    config.save(config_file)

    caplog.set_level(logging.DEBUG)

    with files("resources").joinpath("initial-personal.json").open(
        "rt", encoding="utf-8"
    ) as f:
        raw = json.load(f)
        local_gdrive_client = client.LocalInMemoryClient(raw)

    # act
    exit_code = cli.main(
        ["show", "--config-file", str(config_file), "personal"], local_gdrive_client
    )

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


def test_plan(tmp_path, caplog, capsys, build_config):
    # arrange
    config_file = tmp_path / "config.json"
    config = build_config
    config.save(config_file)

    caplog.set_level(logging.DEBUG)

    with files("resources").joinpath("initial-personal.json").open(
        "rt", encoding="utf-8"
    ) as f:
        raw = json.load(f)
        local_gdrive_client = client.LocalInMemoryClient(raw)

    # act
    exit_code = cli.main(
        ["plan", "--config-file", str(config_file)], local_gdrive_client
    )

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

    report_plans_file = next(config.report_plans_dir.iterdir())
    report_plans_csv = csv.DictReader(report_plans_file.read_text().splitlines())
    assert [
        {k: v for k, v in dataclasses.asdict(report.PlanReport(**row)).items() if v}
        for row in report_plans_csv
    ] == [
        {
            "description": "create an owned folder with same name",
            "end_collection_id": "personal-user@example.com",
            "end_collection_name": "My Drive",
            "end_collection_type": "user",
            "end_entry_name": "Name for folder_1_a",
            "end_entry_path": "Name for personal-top-folder",
            "end_user_access": "owner",
            "end_user_email": "personal-user@example.com",
            "entry_id": "folder_1_a",
            "item_action": "create-folder",
            "item_type": "folder",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for folder_1_a",
            "begin_entry_path": "Name for personal-top-folder",
            "begin_user_access": "reader",
            "begin_user_email": "other-user2@example.com",
            "begin_user_name": "Personal User 2",
            "description": "delete permission for non-owner and not current user",
            "entry_id": "folder_1_a",
            "item_action": "delete-permission",
            "item_type": "folder",
            "permission_id": "folder_1_a-other-user2-reader",
        },
        {
            "description": "create same folder in business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for folder_1_a",
            "end_entry_path": "Name for personal-top-folder",
            "item_action": "create-folder",
            "item_type": "folder",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_1_a",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_1_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a",
            "entry_id": "file_1_a",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "description": "create same folder in business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for folder_2_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a",
            "item_action": "create-folder",
            "item_type": "folder",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_2_a",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_2_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a",
            "entry_id": "file_2_a",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_2_b",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_2_b",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a",
            "entry_id": "file_2_b",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_2_c",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_2_c",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a",
            "entry_id": "file_2_c",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "description": "create same folder in business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for folder_3_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a",
            "item_action": "create-folder",
            "item_type": "folder",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_3_a_a",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a/Name for folder_3_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_3_a_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_a",
            "entry_id": "file_3_a_a",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_2_a_b",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a/Name for folder_3_a",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_2_a_b",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_a",
            "entry_id": "file_2_a_b",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Copy of Name for file_3_b_a",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a/Name for folder_3_b",
            "begin_user_access": "owner",
            "begin_user_email": "personal-user@example.com",
            "begin_user_name": "Personal User",
            "description": "remove 'copy of ' from file name",
            "end_collection_id": "personal-user@example.com",
            "end_collection_name": "My Drive",
            "end_collection_type": "user",
            "end_entry_name": "Name for file_3_b_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_b",
            "end_user_access": "owner",
            "end_user_email": "personal-user@example.com",
            "end_user_name": "Personal User",
            "entry_id": "file_3_b_a",
            "item_action": "rename-file",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Copy of Name for file_3_b_a",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a/Name for folder_3_b",
            "description": "transfer ownership from personal to business account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Copy of Name for file_3_b_a",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_b",
            "entry_id": "file_3_b_a",
            "item_action": "transfer-ownership",
            "item_type": "file",
        },
        {
            "description": "copy file to create a new file owned by the current user",
            "end_collection_id": "personal-user@example.com",
            "end_collection_name": "My Drive",
            "end_collection_type": "user",
            "end_entry_name": "Name for file_3_b_b",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_b",
            "end_user_access": "owner",
            "end_user_email": "personal-user@example.com",
            "entry_id": "file_3_b_b",
            "item_action": "copy-file",
            "item_type": "file",
        },
        {
            "begin_collection_id": "personal-user@example.com",
            "begin_collection_name": "My Drive",
            "begin_collection_type": "user",
            "begin_entry_name": "Name for file_3_b_b",
            "begin_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name "
            "for folder_2_a/Name for folder_3_b",
            "description": "transfer ownership of copied file from personal to business "
            "account",
            "end_collection_id": "example.com.au",
            "end_collection_name": "Shared Drive 1",
            "end_collection_type": "domain",
            "end_entry_name": "Name for file_3_b_b",
            "end_entry_path": "Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_b",
            "item_action": "transfer-owner",
            "item_type": "file",
        },
    ]

    assert [(lvl, msg) for lg, lvl, msg in caplog.record_tuples] == [
        (
            20,
            "Plan modifications for source 'My Drive' in user "
            "'personal-user@example.com'.",
        ),
        (
            20,
            "Plan modifications for target 'Shared Drive 1' in domain 'example.com.au'.",
        ),
        (20, "Starting with folder 'personal-top-folder'."),
        (20, f"Writing entries report '{report_entries_file.name}'."),
        (20, f"Writing permissions report '{report_permissions_file.name}'."),
        (20, f"Writing plans report '{report_plans_file.name}'."),
        (20, "Starting."),
        (
            10,
            "Do not change the top-level folder in the personal account folder 'Name for "
            "personal-top-folder' (id personal-top-folder).",
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
            20,
            'Added plan to "create an owned folder with same name" for entry \'Name for '
            "folder_1_a' path 'Name for personal-top-folder'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (writer)."),
        (10, "Keep permission Personal User 1 <other-user1@example.com> (owner)."),
        (
            20,
            'Added plan to "delete permission for non-owner and not current user" for '
            "entry 'Name for folder_1_a' path 'Name for personal-top-folder'.",
        ),
        (
            20,
            'Added plan to "create same folder in business account" for entry \'Name for '
            "folder_1_a' path 'Name for personal-top-folder'.",
        ),
        (
            10,
            "Folder in business account already exists or will be created folder 'Name "
            "for folder_1_a' (id folder_1_a).",
        ),
        (
            10,
            "Can not transfer ownership of folder in personal account folder 'Name for "
            "folder_1_a' (id folder_1_a).",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_1_a' path 'Name for personal-top-folder/Name for "
            "folder_1_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "create same folder in business account" for entry \'Name for '
            "folder_2_a' path 'Name for personal-top-folder/Name for folder_1_a'.",
        ),
        (
            10,
            "Folder in business account already exists or will be created folder 'Name "
            "for folder_2_a' (id folder_2_a).",
        ),
        (
            10,
            "Can not transfer ownership of folder in personal account folder 'Name for "
            "folder_2_a' (id folder_2_a).",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_2_a' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_2_b' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_2_c' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "create same folder in business account" for entry \'Name for '
            "folder_3_a' path 'Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a'.",
        ),
        (
            10,
            "Folder in business account already exists or will be created folder 'Name "
            "for folder_3_a' (id folder_3_a).",
        ),
        (
            10,
            "Can not transfer ownership of folder in personal account folder 'Name for "
            "folder_3_a' (id folder_3_a).",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_3_a_a' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a/Name for folder_3_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Name for file_2_a_b' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a/Name for folder_3_a'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            10,
            "Folder in business account already exists or will be created folder 'Name "
            "for folder_3_b' (id folder_3_b).",
        ),
        (
            10,
            "Can not transfer ownership of folder in personal account folder 'Name for "
            "folder_3_b' (id folder_3_b).",
        ),
        (20, "Processed 10 entries."),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (
            20,
            "Added plan to \"remove 'copy of ' from file name\" for entry 'Name for "
            "file_3_b_a' path 'Name for personal-top-folder/Name for folder_1_a/Name for "
            "folder_2_a/Name for folder_3_b'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership from personal to business account" for '
            "entry 'Copy of Name for file_3_b_a' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a/Name for folder_3_b'.",
        ),
        (
            10,
            "Getting page 1 of results using '[LocalInMemoryOperationStore] _list: "
            "corpora,fields,includeItemsFromAllDrives,orderBy,pageSize,q,spaces,supportsAllDrives'.",
        ),
        (
            20,
            'Added plan to "copy file to create a new file owned by the current user" '
            "for entry 'Name for file_3_b_b' path 'Name for personal-top-folder/Name for "
            "folder_1_a/Name for folder_2_a/Name for folder_3_b'.",
        ),
        (10, "Keep permission Personal User <personal-user@example.com> (reader)."),
        (10, "Keep permission Personal User 1 <other-user1@example.com> (owner)."),
        (
            20,
            'Added plan to "transfer ownership of copied file from personal to business '
            "account\" for entry 'Name for file_3_b_b' path 'Name for "
            "personal-top-folder/Name for folder_1_a/Name for folder_2_a/Name for "
            "folder_3_b'.",
        ),
        (20, "Finished."),
    ]


def test_apply(tmp_path, caplog, capsys, build_config):
    # arrange
    config_file = tmp_path / "config.json"
    config = build_config
    config.save(config_file)

    caplog.set_level(logging.DEBUG)

    with files("resources").joinpath("initial-personal.json").open(
        "rt", encoding="utf-8"
    ) as f:
        raw = json.load(f)
        local_gdrive_client = client.LocalInMemoryClient(raw)

    plan_file = tmp_path / "plan.csv"

    # act
    # TODO
    with pytest.raises(FileNotFoundError):
        exit_code = cli.main(
            ["apply", "--config-file", str(config_file), str(plan_file)],
            local_gdrive_client,
        )

    # assert
    # assert exit_code == 1

    stdout, stderr = capsys.readouterr()
    assert stdout == ""
    assert stderr == ""
