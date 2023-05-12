import re

import pytest

from file_mover_for_google_drive.common import models


pytest.register_assert_rewrite("helpers")


@pytest.fixture()
def equal_ignore_whitespace():
    def _equal_ignore_whitespace(value1: str, value2: str, ignore_case=False):
        # Ignore non-space and non-word characters
        whitespace = re.compile(r"\s+")
        replace1 = whitespace.sub(" ", value1 or "").strip()
        replace2 = whitespace.sub(" ", value2 or "").strip()

        if ignore_case:
            assert replace1.casefold() == replace2.casefold()
        else:
            assert replace1 == replace2

    return _equal_ignore_whitespace


@pytest.fixture
def build_config():
    def _build(top_dir, account_type: models.GoogleDriveAccountTypeOptions):
        credentials_file = top_dir / "credentials.json"
        credentials_file.touch(exist_ok=True)

        token_file = top_dir / "token.json"

        auth = models.ConfigAuth(
            credentials_file=credentials_file, token_file=token_file
        )

        entries_dir = top_dir / "reports-entries"
        permissions_dir = top_dir / "reports-permissions"
        plans_dir = top_dir / "reports-plans"
        outcomes_dir = top_dir / "reports-outcomes"

        reports = models.ConfigReports(
            entries_dir=entries_dir,
            permissions_dir=permissions_dir,
            plans_dir=plans_dir,
            outcomes_dir=outcomes_dir,
        )

        actions = models.ConfigActions(
            permissions_delete_other_users=True,
            permissions_delete_link=True,
            entry_name_delete_prefix_copy_of=False,
            create_owned_file_copy=True,
            create_owned_folder_and_move_contents=True,
            permissions_user_emails_keep=[],
            allow_changing_top_folder=False,
        )

        if account_type == models.GoogleDriveAccountTypeOptions.PERSONAL:
            account = models.ConfigAccount(
                account_type=account_type,
                drive_id=models.ConfigAccount.drive_name_my_drive(),
                account_id="personal-current-user@example.com",
                top_folder_id="personal-folder-level0",
            )
        elif account_type == models.GoogleDriveAccountTypeOptions.BUSINESS:
            account = models.ConfigAccount(
                account_type=account_type,
                drive_id="example-shared-drive-1-id",
                account_id="example.com.au",
                top_folder_id="business-folder-level0",
            )
        else:
            raise ValueError(f"Unknown account type '{account_type}',")

        config = models.ConfigProgram(
            auth=auth, reports=reports, actions=actions, account=account
        )
        return config

    return _build
