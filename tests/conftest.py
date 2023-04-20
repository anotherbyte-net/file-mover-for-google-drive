import re

import pytest

from file_mover_for_google_drive.common import models


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
def build_config(tmp_path):
    auth_credentials_file = tmp_path / "credentials.json"
    auth_credentials_file.touch(exist_ok=True)

    auth_token_file = tmp_path / "token.json"

    report_entries_dir = tmp_path / "reports-entries"
    report_permissions_dir = tmp_path / "reports-permissions"
    report_plans_dir = tmp_path / "reports-plans"
    report_outcomes_dir = tmp_path / "reports-outcomes"

    action_remove_prefix_copy_of = True
    action_permissions_remove_users = True
    action_permissions_remove_anyone = True
    action_copy_unowned = True
    action_move_to_owned_folder = True
    action_transfer_ownership = True

    personal_account_top_folder_id = "personal-top-folder"
    personal_account_email = "personal-user@example.com"

    business_account_top_folder_id = "business-top-folder"
    business_account_shared_drive = "Shared Drive 1"
    business_account_domain = "example.com.au"

    config = models.Config(
        auth_credentials_file=auth_credentials_file,
        auth_token_file=auth_token_file,
        report_entries_dir=report_entries_dir,
        report_permissions_dir=report_permissions_dir,
        report_plans_dir=report_plans_dir,
        report_outcomes_dir=report_outcomes_dir,
        action_remove_prefix_copy_of=action_remove_prefix_copy_of,
        action_permissions_remove_users=action_permissions_remove_users,
        action_permissions_remove_anyone=action_permissions_remove_anyone,
        action_copy_unowned=action_copy_unowned,
        action_move_to_owned_folder=action_move_to_owned_folder,
        action_transfer_ownership=action_transfer_ownership,
        personal_account_top_folder_id=personal_account_top_folder_id,
        personal_account_email=personal_account_email,
        business_account_top_folder_id=business_account_top_folder_id,
        business_account_shared_drive=business_account_shared_drive,
        business_account_domain=business_account_domain,
    )
    return config
