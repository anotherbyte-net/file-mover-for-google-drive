"""The plan action."""

import dataclasses
import logging
import typing

from file_mover_for_google_drive.common import manage, models, report, client

logger = logging.getLogger(__name__)


class Plan(manage.BaseManage):
    """
    Build a plan for making changes to two Google Drive accounts,
    one personal and one business.
    """

    def __init__(
        self, config: models.ConfigProgram, gd_client: client.GoogleApiClient = None
    ) -> None:
        """Create a new Plan instance."""

        super().__init__(config, gd_client)

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
                self._process_one,
                rpt_entries=rpt_entries,
                rpt_permissions=rpt_permissions,
                rpt_plans=rpt_plans,
            )
            return result

    def _process_one(
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

        top_folder_id = config.account.top_folder_id
        account = config.account
        account_id = account.account_id

        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])

        if entry.entry_id == top_folder_id:
            logger.debug("Will not change the top-level folder '%s'.", entry.name)
            return None

        for plan_item in self._build_plan_unowned(entry, parent_path_str):
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

        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        role_owner = models.GoogleDrivePermissionRoleOptions.owner

        container = self._container
        config = self._config
        actions = self._actions

        key_original = config.custom_prop_original_key
        key_copy = config.custom_prop_copy_key

        account = config.account
        account_id = account.account_id
        account_type = account.account_type

        if account_type != account_type_personal:
            raise ValueError(
                "File and folder ownership cannot be changed in a business "
                "account by copying. copied changes are only. Use the Google Drive "
                "website to change permissions in a business account."
            )

        is_owned = entry.is_owned_by(account_id)
        if is_owned:
            logging.debug("Will never copy an owned file or folder.")
            return None

        # only assess unowned entries - files
        if not entry.is_dir:
            if not config.actions.create_owned_file_copy:
                logger.debug(
                    "Config prevented creating an owned copy of file '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return None

            # check if there is already a copy of the file

            # does this file have the property that indicates there is a copy?
            prop_copy_entry_id = entry.properties_shared.get(key_copy)
            if prop_copy_entry_id:
                other_entry = actions.get_entry(prop_copy_entry_id)
            else:
                # is there another file that has a property that indicates that this
                # file is it's original?
                other_entry = actions.get_pair_copy_entry(entry)

            # if there is not a copy of the file, then copy it
            # otherwise, just log the existence of the copy.
            if other_entry:
                logging.debug(
                    "Found existing copy of file '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
            else:
                # create an owned copy of the unowned file
                yield self._plan_builder.get_copy_file(
                    entry=entry,
                    user_email=account_id,
                    user_access=role_owner,
                    entry_path=parent_path_str,
                )

        # only assess unowned entries - folders
        if entry.is_dir:
            if not config.actions.create_owned_folder_and_move_contents:
                logger.debug(
                    "Config prevented creating an owned folder and moving contents for "
                    "'%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
                return None
            # check if there is already another folder with the same parent and same
            # name

            # does this folder have the property that indicates there is a copy?
            prop_copy_entry_id = entry.properties_shared.get(key_copy)
            if prop_copy_entry_id:
                other_entry = actions.get_entry(prop_copy_entry_id)
            else:
                # is there another folder that has a property that indicates that this
                # folder is it's original?
                other_entry = actions.get_pair_copy_entry(entry)

            # if there is not another of the folder, then create one
            # otherwise, just log the existence of the copy.
            if other_entry:
                logging.debug(
                    "Found existing copy of folder '%s' at '%s'.",
                    entry.name,
                    parent_path_str,
                )
            else:
                # create an owned copy of the unowned folder
                yield self._plan_builder.get_create_folder(
                    entry=entry,
                    user_email=account_id,
                    user_access=role_owner,
                    entry_path=parent_path_str,
                )

            # TODO: move the contents of the unowned folder into the owned folder
            a = 1

    def _build_plan_rename(
        self, entry: models.GoogleDriveEntry, parent_path_str: str
    ) -> typing.Iterable[report.PlanReport]:
        """Rename an owned file."""
        actions = self._config.actions
        is_rename = actions.entry_name_delete_prefix_copy_of is True

        entry_owner = entry.permission_owner_user

        if not entry_owner:
            logger.debug("Will never rename unowned entries.")
            return None

        if entry.is_dir:
            logger.debug("Will never rename folders.")
            return None

        prefix_copy = "Copy of ".casefold()
        prefix_copy_len = len(prefix_copy)
        compare_name = str(entry.name).casefold()
        rename_index = 0
        while compare_name[rename_index:].startswith(prefix_copy):
            # there might be more than one instance of the prefix
            rename_index += prefix_copy_len

        if rename_index < 1:
            logger.debug("No change to file name.")
            return None

        new_name = entry.name[rename_index:]

        if not is_rename:
            logger.debug(
                "Config prevented renaming '%s' to '%s'.", entry.name, new_name
            )
            return None

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

        account_type_personal = models.GoogleDriveAccountTypeOptions.personal
        role_owner = models.GoogleDrivePermissionRoleOptions.owner
        permission_user = models.GoogleDrivePermissionTypeOptions.user
        permission_anyone = models.GoogleDrivePermissionTypeOptions.anyone

        account = self._config.account
        actions = self._config.actions

        account_id = account.account_id
        account_type = account.account_type

        is_delete_link = actions.permissions_delete_link is True
        is_delete_others = actions.permissions_delete_other_users is True

        if account_type != account_type_personal:
            raise ValueError(
                "Permission changes are only implemented for personal "
                f"accounts, not '{account_type}'. Use the Google Drive website to "
                "change permissions in a business account."
            )

        for permission in entry.permissions_all:
            is_owner = permission.role == role_owner
            is_anyone = permission.entry_type == permission_anyone
            is_user = permission.entry_type == permission_user
            is_current_user = is_user and permission.user_email == account_id
            is_user_not_current = is_user and not permission.user_email == account_id

            if is_owner or is_current_user:
                logger.debug("Keep permission %s.", str(permission))
                continue

            elif is_anyone and is_delete_link:
                logger.debug("Delete permission %s.", str(permission))
                yield self._plan_builder.get_delete_permission(
                    entry=entry,
                    permission=permission,
                    entry_path=parent_path_str,
                )
                continue

            elif is_anyone and not is_delete_link:
                logger.debug(
                    "Config prevented deleting permission %s.", str(permission)
                )
                continue

            elif is_user_not_current and is_delete_others:
                logger.debug("Delete permission %s.", str(permission))
                yield self._plan_builder.get_delete_permission(
                    entry=entry,
                    permission=permission,
                    entry_path=parent_path_str,
                )
                continue

            elif is_user_not_current and not is_delete_others:
                logger.debug(
                    "Config prevented deleting permission %s.", str(permission)
                )
                continue

            raise ValueError(f"Unknown permission {str(permission)}.")
