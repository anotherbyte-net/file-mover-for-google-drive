"""Build reports for different types of plans."""

from file_mover_for_google_drive.common import report, models


class PlanReportBuilder:
    def __init__(self, account: models.ConfigAccount):
        self._account = account

    def check_create_folder(self, entry: models.GoogleDriveEntry) -> None:
        if not entry.is_dir:
            raise ValueError(f"Entry is not a folder '{entry.name}'.")

        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

    def get_create_folder(
        self,
        entry: models.GoogleDriveEntry,
        user_name: str,
        user_email: str,
        user_access: models.GoogleDrivePermissionRoleOptions,
        entry_path: str,
    ) -> report.PlanReport:
        self.check_create_folder(entry)
        return report.PlanReport(
            item_action=models.PlanReportActions.create_folder.value,
            item_type=entry.entry_type,
            entry_id=entry.entry_id,
            permission_id=None,
            description="create an owned folder with same name",
            account_type=self._account.account_type.value,
            account_id=self._account.account_id,
            drive_id=self._account.drive_id,
            begin_user_name=None,
            begin_user_email=None,
            begin_user_access=None,
            begin_entry_name=None,
            begin_entry_path=None,
            end_user_name=user_name,
            end_user_email=user_email,
            end_user_access=user_access.value,
            end_entry_name=entry.name,
            end_entry_path=entry_path,
        )

    def check_copy_file(self, entry: models.GoogleDriveEntry) -> None:
        if entry.is_dir:
            raise ValueError(f"Entry is not a file '{entry.name}'.")

        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

    def get_copy_file(
        self,
        entry: models.GoogleDriveEntry,
        user_name: str,
        user_email: str,
        user_access: models.GoogleDrivePermissionRoleOptions,
        entry_path: str,
    ) -> report.PlanReport:
        self.check_copy_file(entry)
        current_owner = entry.permission_owner_user
        return report.PlanReport(
            item_action=models.PlanReportActions.copy_file.value,
            item_type=entry.entry_type,
            entry_id=entry.entry_id,
            permission_id=None,
            description="copy file to create a new file owned by the current user",
            account_type=self._account.account_type.value,
            account_id=self._account.account_id,
            drive_id=self._account.drive_id,
            begin_user_name=current_owner.display_name,
            begin_user_email=current_owner.user_email,
            begin_user_access=current_owner.role.value,
            begin_entry_name=entry.name,
            begin_entry_path=entry_path,
            end_user_name=user_name,
            end_user_email=user_email,
            end_user_access=user_access.value,
            end_entry_name=entry.name,
            end_entry_path=entry_path,
        )

    def get_rename_file(
        self,
        new_name: str,
        entry: models.GoogleDriveEntry,
        permission: models.GoogleDrivePermission,
        entry_path: str,
    ) -> report.PlanReport:
        if entry.is_dir:
            raise ValueError(f"Entry is not a file '{entry.name}'.")

        account_type_business = models.GoogleDriveAccountTypeOptions.business
        if self._account.account_type != account_type_business:
            raise ValueError(
                f"Not a business account '{self._account.account_type.name}'."
            )

        return report.PlanReport(
            item_action=models.PlanReportActions.rename_file.value,
            item_type=entry.entry_type,
            entry_id=entry.entry_id,
            permission_id=None,
            description="rename file",
            account_type=self._account.account_type.value,
            account_id=self._account.account_id,
            drive_id=self._account.drive_id,
            begin_user_name=permission.display_name,
            begin_user_email=permission.user_email,
            begin_user_access=permission.role.value,
            begin_entry_name=entry.name,
            begin_entry_path=entry_path,
            end_user_name=permission.display_name,
            end_user_email=permission.user_email,
            end_user_access=permission.role.value,
            end_entry_name=new_name,
            end_entry_path=entry_path,
        )

    def get_delete_permission(
        self,
        entry: models.GoogleDriveEntry,
        permission: models.GoogleDrivePermission,
        entry_path: str,
    ) -> report.PlanReport:
        perm_role_owner = models.GoogleDrivePermissionRoleOptions.owner.value
        if permission.role == perm_role_owner:
            raise ValueError("Cannot delete 'owner' role.")

        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

        return report.PlanReport(
            item_action=models.PlanReportActions.delete_permission.value,
            item_type=entry.entry_type,
            entry_id=entry.entry_id,
            permission_id=permission.entry_id,
            description="delete permission for non-owner and not current user",
            account_type=self._account.account_type.value,
            account_id=self._account.account_id,
            drive_id=self._account.drive_id,
            begin_user_name=permission.display_name,
            begin_user_email=permission.user_email,
            begin_user_access=permission.role.value,
            begin_entry_name=entry.name,
            begin_entry_path=entry_path,
            end_user_name=None,
            end_user_email=None,
            end_user_access=None,
            end_entry_name=None,
            end_entry_path=None,
        )

    def get_move_entry(
        self,
        entry: models.GoogleDriveEntry,
        user_name: str,
        user_email: str,
        user_access: models.GoogleDrivePermissionRoleOptions,
        entry_path: str,
    ) -> report.PlanReport:
        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

        return report.PlanReport(
            item_action=models.PlanReportActions.move_entry.value,
            item_type=entry.entry_type,
            entry_id=entry.entry_id,
            permission_id=None,
            description="move an entry from an unowned folder to an owned folder",
            account_type=self._account.account_type.value,
            account_id=self._account.account_id,
            drive_id=self._account.drive_id,
            begin_user_name=user_name,
            begin_user_email=user_email,
            begin_user_access=user_access.value,
            begin_entry_name=entry.name,
            begin_entry_path=entry_path,
            end_user_name=user_name,
            end_user_email=user_email,
            end_user_access=user_access.value,
            end_entry_name=entry.name,
            end_entry_path=entry_path,
        )
