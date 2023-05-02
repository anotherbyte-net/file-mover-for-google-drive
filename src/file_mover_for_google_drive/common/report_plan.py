"""Build reports for different types of plans."""
import typing

from file_mover_for_google_drive.common import report, models


class PlanReportBuilder:
    """A class that helps build plan report items."""

    def __init__(self, account: models.ConfigAccount):
        self._account = account

    def check_create_folder(self, entry: models.GoogleDriveEntry) -> None:
        """Check that the requirements for creating a folder are fulfilled.

        Args:
            entry: The folder instance.

        Returns:
            None
        """
        if not entry.is_dir:
            raise ValueError(f"Entry is not a folder '{entry.name}'.")

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
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
        """Build a plan report item that creates a folder.

        Args:
            entry: The folder instance.
            user_name: The username for the permission.
            user_email: The email for the permission.
            user_access: The role for the permission.
            entry_path: The path to this folder.

        Returns:
            A plan report item for creating a folder.
        """
        self.check_create_folder(entry)
        return report.PlanReport(
            item_action=models.PlanReportActions.CREATE_FOLDER.value,
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

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
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
            item_action=models.PlanReportActions.COPY_FILE.value,
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

    def check_rename_file(
        self, entry: typing.Optional[models.GoogleDriveEntry]
    ) -> None:
        if not entry:
            raise ValueError("Must provide entry.")

        if entry.is_dir:
            raise ValueError(f"Entry is not a file '{entry.name}'.")

        account_type_business = models.GoogleDriveAccountTypeOptions.BUSINESS
        if self._account.account_type != account_type_business:
            raise ValueError(
                f"Not a business account '{self._account.account_type.name}'."
            )

    def get_rename_file(
        self,
        new_name: str,
        entry: models.GoogleDriveEntry,
        permission: models.GoogleDrivePermission,
        entry_path: str,
    ) -> report.PlanReport:
        self.check_rename_file(entry)
        return report.PlanReport(
            item_action=models.PlanReportActions.RENAME_FILE.value,
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

    def check_delete_permission(
        self, permission: typing.Optional[models.GoogleDrivePermission]
    ) -> None:
        if not permission:
            raise ValueError("Must provide permission.")

        perm_role_owner = models.GoogleDrivePermissionRoleOptions.OWNER.value
        if permission.role == perm_role_owner:
            raise ValueError("Cannot delete 'owner' role.")

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

    def get_delete_permission(
        self,
        entry: models.GoogleDriveEntry,
        permission: models.GoogleDrivePermission,
        entry_path: str,
    ) -> report.PlanReport:
        self.check_delete_permission(permission)
        return report.PlanReport(
            item_action=models.PlanReportActions.DELETE_PERMISSION.value,
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

    def check_move_entry(self) -> None:
        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        if self._account.account_type != account_type_personal:
            raise ValueError(
                f"Not a personal account '{self._account.account_type.name}'."
            )

    def get_move_entry(
        self,
        entry: models.GoogleDriveEntry,
        user_name: str,
        user_email: str,
        user_access: models.GoogleDrivePermissionRoleOptions,
        entry_path: str,
    ) -> report.PlanReport:
        self.check_move_entry()
        return report.PlanReport(
            item_action=models.PlanReportActions.MOVE_ENTRY.value,
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
