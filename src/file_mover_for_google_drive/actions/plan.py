"""The plan action."""

import dataclasses
import logging
import pathlib
import typing

from file_mover_for_google_drive.common import manage, models, report, client

logger = logging.getLogger(__name__)


class Plan(manage.BaseManage):
    """
    Build a plan for making changes to two Google Drive accounts,
    one personal and one business.
    """

    def __init__(
        self,
        config: models.ConfigProgram,
        gd_client: typing.Optional[client.GoogleApiClient] = None,
    ) -> None:
        """Create a new Apply instance."""
        super().__init__(config=config, allow_modify=False, gd_client=gd_client)

    def run(self) -> bool:
        """Run the 'apply' action."""
        config = self._config

        account = config.account

        entries_dir = config.reports.entries_dir
        perms_dir = config.reports.permissions_dir
        plans_dir = config.reports.plans_dir

        logger.info(
            "Plan modifications for %s account '%s'.",
            account.account_type.name,
            account.account_id,
        )

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(perms_dir, report.PermissionReport)
        rpt_plans = report.ReportCsv(plans_dir, report.PlanReport)

        # build
        with rpt_entries, rpt_permissions, rpt_plans:
            logger.info("Writing entries report '%s'.", rpt_entries.path.name)
            logger.info("Writing permissions report '%s'.", rpt_permissions.path.name)
            logger.info("Writing plans report '%s'.", rpt_plans.path.name)

            result = self._iterate_entries(
                self.process_one,
                rpt_entries=rpt_entries,
                rpt_permissions=rpt_permissions,
                rpt_plans=rpt_plans,
            )
            return result

    def process_one(
        self,
        entry: models.GoogleDriveEntry,
        rpt_entries: report.ReportCsv,
        rpt_permissions: report.ReportCsv,
        rpt_plans: report.ReportCsv,
    ) -> None:
        """Process one entry."""

        cache = self._cache
        cache.add(entry)

        entry_path = cache.path(entry.entry_id)
        logger.info("Processing %s.", str(entry))

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)

        for rpt_item in self._build_plans(entry_path):
            logger.info("Added plan %s.", str(rpt_item))
            row = dataclasses.asdict(rpt_item)
            rpt_plans.write_item(row)

    def _build_plans(
        self, entry_path: list[models.GoogleDriveEntry]
    ) -> typing.Iterable[report.PlanReport]:
        """Build plan items to represent the changes to make."""

        config = self._config

        entry = entry_path[-1]
        parent = entry_path[-2] if len(entry_path) > 1 else None
        parent_path_str = entry.build_path_str(entry_path[:-1])

        if not config.actions.allow_changing_top_folder:
            account = config.account
            top_folder_id = account.top_folder_id
            if entry.entry_id == top_folder_id:
                logger.debug("Will not change the top-level folder '%s'.", entry.name)
                return

        for plan_item in self._build_plan_unowned(entry, parent_path_str):
            if plan_item:
                yield plan_item

        for plan_item in self._build_plan_move(entry, parent, parent_path_str):
            if plan_item:
                yield plan_item

        for plan_item in self._build_plan_rename(entry, parent_path_str):
            if plan_item:
                yield plan_item

        for plan_item in self._build_plan_permissions(entry, parent_path_str):
            if plan_item:
                yield plan_item

    def _build_plan_unowned(
        self, entry: models.GoogleDriveEntry, parent_path_str: str
    ) -> typing.Iterable[report.PlanReport]:
        """Create owned copies of files and folders."""

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        role_owner = models.GoogleDrivePermissionRoleOptions.OWNER

        config = self._config
        actions = self._actions

        account = config.account
        account_id = account.account_id
        account_type = account.account_type

        if account_type != account_type_personal:
            raise ValueError(
                "File and folder ownership fixes by copying files and folders "
                "are only implemented for personal "
                f"accounts, not '{account_type}'. Use the Google Drive website to "
                "change ownership and access for other account types."
            )

        is_owned = entry.is_owned_by(account_id)
        if is_owned:
            logger.debug("Will never copy an owned file or folder.")
            return

        # only assess unowned entries - folders
        if entry.is_dir:
            if not config.actions.create_owned_folder_and_move_contents:
                logger.debug(
                    "Config prevented creating an owned folder and moving contents for "
                    "'%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return

            # check if there is already another folder
            # with the same parent and same name

            # is there another entry that has a property that indicates that this
            # entry is it's original?
            owned_entry = actions.get_pair_copy_entry(entry)

            # if there is not another of the folder, then create one
            # otherwise, just log the existence of the copy.
            if owned_entry:
                logger.info(
                    "Found existing copy of folder '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return

            # create an owned copy of the unowned folder
            current_user_permission = entry.get_permission_by_email(account_id)
            yield self._plan_builder.get_create_folder(
                entry=entry,
                user_name=models.GoogleDrivePermission.get_display_name(
                    current_user_permission
                ),
                user_email=account_id,
                user_access=role_owner,
                entry_path=parent_path_str,
            )

        # only assess unowned entries - files
        if not entry.is_dir:
            if not config.actions.create_owned_file_copy:
                logger.debug(
                    "Config prevented creating an owned copy of file '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return

            # check if there is already a copy of the file

            # is there another entry that has a property that indicates that this
            # entry is it's original?
            owned_entry = actions.get_pair_copy_entry(entry)

            if owned_entry and owned_entry.is_dir:
                raise ValueError(
                    f"Searched for copy of {str(entry)}. "
                    f"Match was not a file: {str(owned_entry)}."
                )

            # if there is not a copy of the file, then copy it
            # otherwise, just log the existence of the copy.
            if owned_entry:
                logger.info(
                    "Found existing copy of file '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return

            # create an owned copy of the unowned file
            current_user_permission = entry.get_permission_by_email(account_id)
            yield self._plan_builder.get_copy_file(
                entry=entry,
                user_name=models.GoogleDrivePermission.get_display_name(
                    current_user_permission
                ),
                user_email=account_id,
                user_access=role_owner,
                entry_path=parent_path_str,
            )

    def _build_plan_rename(
        self, entry: models.GoogleDriveEntry, parent_path_str: str
    ) -> typing.Iterable[report.PlanReport]:
        """Rename an owned file."""
        config_actions = self._config.actions
        is_rename = config_actions.entry_name_delete_prefix_copy_of is True

        entry_owner = entry.permission_owner_user

        if not entry_owner:
            logger.debug("Will never rename unowned entries.")
            return

        if entry.is_dir:
            logger.debug("Will never rename folders.")
            return

        prefix_copy = "Copy of ".casefold()
        prefix_copy_len = len(prefix_copy)
        compare_name = str(entry.name).casefold()
        rename_index = 0
        count = 0

        # there might be zero, one, or more instances of the prefix
        while compare_name[rename_index:].startswith(prefix_copy):
            count += 1
            rename_index += prefix_copy_len

        if rename_index < 1:
            logger.debug("No change to file name.")
            return

        new_name = pathlib.Path(entry.name[rename_index:])

        # Add the number of copies to the end of the file name.
        # Check if the number of copies is already present.
        # Combine the numbers if the number of copies is already present.
        copy_count_text = " copy (x"
        if copy_count_text in new_name.stem and new_name.stem.endswith(")"):
            count_copy_index = new_name.stem.rindex(copy_count_text) + len(
                copy_count_text
            )
            count_copy = new_name.stem[count_copy_index:-1]
            count += int(count_copy)

        new_name = f"{new_name.stem}{copy_count_text}{count}){new_name.suffix}"

        if not is_rename:
            logger.debug(
                "Config prevented renaming '%s' to '%s'.", entry.name, new_name
            )
            return

        logger.debug("Rename '%s' to '%s'.", entry.name, new_name)
        yield self._plan_builder.get_rename_file(
            new_name=new_name,
            entry=entry,
            permission=entry_owner,
            entry_path=parent_path_str,
        )

    def _build_plan_permissions(
        self, entry: models.GoogleDriveEntry, parent_path_str: str
    ) -> typing.Iterable[report.PlanReport]:
        """Remove permissions for an entry (owned and unowned), except current user
        and owner."""

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        role_owner = models.GoogleDrivePermissionRoleOptions.OWNER
        permission_user = models.GoogleDrivePermissionTypeOptions.USER
        permission_anyone = models.GoogleDrivePermissionTypeOptions.ANYONE

        account = self._config.account
        config_actions = self._config.actions

        account_id = account.account_id
        account_type = account.account_type

        is_delete_link = config_actions.permissions_delete_link is True
        is_delete_others = config_actions.permissions_delete_other_users is True
        keep_emails = config_actions.permissions_user_emails_keep or []

        if account_type != account_type_personal:
            raise ValueError(
                "Permission changes are only implemented for personal "
                f"accounts, not '{account_type}'. Use the Google Drive website to "
                "change permissions for other account types."
            )

        for permission in entry.permissions_all:
            is_owner = permission.role == role_owner
            is_anyone = permission.entry_type == permission_anyone
            is_user = permission.entry_type == permission_user

            perm_user_email = permission.user_email
            is_current_user = is_user and perm_user_email == account_id
            is_user_not_current = is_user and not perm_user_email == account_id

            if is_owner or is_current_user:
                logger.debug("Keep permission %s.", str(permission))
                continue

            if is_anyone and is_delete_link:
                logger.debug("Delete permission %s.", str(permission))
                yield self._plan_builder.get_delete_permission(
                    entry=entry,
                    permission=permission,
                    entry_path=parent_path_str,
                )
                continue

            if is_anyone and not is_delete_link:
                logger.debug(
                    "Config prevented deleting permission %s.", str(permission)
                )
                continue

            if perm_user_email in keep_emails:
                logger.debug(
                    "Config prevented deleting permission %s.", str(permission)
                )
                continue

            if is_user_not_current and is_delete_others:
                logger.debug("Delete permission %s.", str(permission))
                yield self._plan_builder.get_delete_permission(
                    entry=entry,
                    permission=permission,
                    entry_path=parent_path_str,
                )
                continue

            if is_user_not_current and not is_delete_others:
                logger.debug(
                    "Config prevented deleting permission %s.", str(permission)
                )
                continue

            raise ValueError(f"Unknown permission {str(permission)}.")

    def _build_plan_move(
        self,
        entry: models.GoogleDriveEntry,
        parent: typing.Optional[models.GoogleDriveEntry],
        parent_path_str: str,
    ) -> typing.Iterable[report.PlanReport]:
        """Move the contents of unowned folders into the created owned folder."""

        # NOTE: the 'move-entry' plan uses the entry id of the unowned entry,
        # as the copy may not exist yet (so can't use the copy's id).

        if not parent:
            return

        account_type_personal = models.GoogleDriveAccountTypeOptions.PERSONAL
        role_owner = models.GoogleDrivePermissionRoleOptions.OWNER

        config = self._config
        actions = self._actions

        account = config.account
        account_id = account.account_id
        account_type = account.account_type

        if account_type != account_type_personal:
            raise ValueError(
                "File and folder ownership fixes by moving files and folders "
                "are only implemented for personal "
                f"accounts, not '{account_type}'. Use the Google Drive website to "
                "change ownership and access for other account types."
            )

        is_parent_owned = parent.is_owned_by(account_id)
        if is_parent_owned:
            logger.debug("Will never move files and folders in an owned folder.")
            return

        is_entry_owned = entry.is_owned_by(account_id)
        if not is_entry_owned:
            # check for an owned copy of the entry

            # is there another entry that has a property that indicates that this
            # entry is it's original?
            owned_entry = actions.get_pair_copy_entry(entry)

            # if there is an owned copy of the entry,
            # check if the owned copy needs to be moved
            if owned_entry:
                other_parent = actions.get_entry(owned_entry.parent_id)
                is_other_parent_owned = other_parent.is_owned_by(account_id)
                if is_other_parent_owned:
                    logger.debug(
                        "Unowned file or folder has an owned copy "
                        "and the copy has already been moved."
                    )
                    return

        if not config.actions.create_owned_folder_and_move_contents:
            logger.debug(
                "Config prevented moving entry '%s' in unowned folder '%s'.",
                entry.name,
                parent_path_str,
            )
            return

        current_user_permission = entry.get_permission_by_email(account_id)
        yield self._plan_builder.get_move_entry(
            entry=entry,
            user_name=models.GoogleDrivePermission.get_display_name(
                current_user_permission
            ),
            user_email=account_id,
            user_access=role_owner,
            entry_path=parent_path_str,
        )
