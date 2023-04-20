"""The plan action."""

import dataclasses
import logging
import typing

from file_mover_for_google_drive.common import manage, models, interact, utils, report

logger = logging.getLogger(__name__)


class Plan(manage.BaseManage):
    """Build a plan for making changes to two Google Drive accounts, one personal and one business."""

    def __init__(self, config: models.Config, client=None):
        """Create a new Plan instance."""

        super().__init__(config, client)
        self._bus_folders_path_create: list[str] = []

    def run(self) -> bool:
        """Run the 'apply' action."""
        per_container = self._personal_container
        bus_container = self._business_container

        config = self._config
        per_actions = interact.GoogleDriveActions(per_container)

        per_top_folder_id = config.personal_account_top_folder_id
        per_container_cache = utils.GoogleDriveEntryCache(per_top_folder_id)

        per_col_type = per_container.collection_type
        per_col_name = per_container.collection_name
        per_col_id = per_container.collection_id

        bus_col_type = bus_container.collection_type
        bus_col_name = bus_container.collection_name
        bus_col_id = bus_container.collection_id

        entries_dir = config.report_entries_dir
        perms_dir = config.report_permissions_dir
        plans_dir = config.report_plans_dir

        self._bus_folders_path_create = []

        log_batch_size = 40

        logger.info(
            f"Plan modifications for source '{per_col_name}' in {per_col_type} '{per_col_id}'."
        )
        logger.info(
            f"Plan modifications for target '{bus_col_name}' in {bus_col_type} '{bus_col_id}'."
        )
        logger.info(f"Starting with folder '{per_top_folder_id}'.")

        # allow cancelling without issues
        graceful_exit = utils.GracefulExit()

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(perms_dir, report.PermissionReport)
        rpt_plans = report.ReportCsv(plans_dir, report.PlanReport)

        # build
        with rpt_entries, rpt_permissions, rpt_plans:
            logger.info(f"Writing entries report '{rpt_entries.path.name}'.")
            logger.info(f"Writing permissions report '{rpt_permissions.path.name}'.")
            logger.info(f"Writing plans report '{rpt_plans.path.name}'.")

            logger.info("Starting.")

            entry_count = 0

            # top entry
            per_top_entry = per_actions.get_entry(per_top_folder_id)
            entry_count += 1
            self._process_one(
                per_container_cache,
                rpt_entries,
                rpt_permissions,
                rpt_plans,
                per_top_entry,
            )

            # descendants
            for index, entry in enumerate(
                per_actions.get_descendants(per_top_folder_id)
            ):
                entry_count += 1

                self._process_one(
                    per_container_cache, rpt_entries, rpt_permissions, rpt_plans, entry
                )

                if index > 0 and index % log_batch_size == 0:
                    logger.info(f"Processed {index + 1} entries.")

                if graceful_exit.should_exit():
                    logger.warning("Stopping early.")
                    break

        logger.info("Finished.")

        return False if graceful_exit.should_exit() else True

    def _process_one(
        self, container_cache, rpt_entries, rpt_permissions, rpt_plans, entry
    ):
        """Process one entry."""

        container_cache.add(entry)

        entry_path = container_cache.path(entry.entry_id)

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)

        for rpt_item in self._gather_changes(entry_path):
            logger.info("Added plan to %s.", str(rpt_item))
            row = dataclasses.asdict(rpt_item)
            rpt_plans.write_item(row)

    def _gather_changes(
        self, entry_path: list[models.GoogleDriveEntry]
    ) -> typing.Iterable[report.PlanReport]:
        """Build plan items to represent the changes to make."""

        # Note: See the readme for the changes to be made.

        # As a summary: Tidy permissions and ownership in the personal account to
        # prepare for moving files and folders to a business account by transferring ownership.

        per_container = self._personal_container
        bus_container = self._business_container

        config = self._config
        api = self._api

        per_actions = interact.GoogleDriveActions(per_container)

        per_top_folder_id = config.personal_account_top_folder_id
        per_account_email = config.personal_account_email

        per_col_type = per_container.collection_type
        per_col_name = per_container.collection_name
        per_col_id = per_container.collection_id

        bus_col_type = bus_container.collection_type
        bus_col_name = bus_container.collection_name
        bus_col_id = bus_container.collection_id

        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])
        per_is_owned = entry.is_owned_by(per_account_email)
        entry_owner = entry.permission_owner_user

        # if this entry is the personal top folder, don't make any changes
        if entry.entry_id == per_top_folder_id:
            logger.debug(
                "Do not change the top-level folder in the personal account %s.",
                str(entry),
            )
            return []

        # copy unowned items first
        if not per_is_owned:
            # check for existing copy
            entry_paired = per_actions.get_pair(entry)
            copy_id = entry.custom_property(config.custom_prop_copy_key)

            if entry_paired and copy_id and entry_paired.entry_id != copy_id:
                raise ValueError(
                    f"Copy id '{copy_id}' does not match "
                    f"the pair id '{entry_paired.entry_id}' "
                    f"for original {str(entry)}."
                )

            if not copy_id and not entry_paired:
                if entry.is_dir:
                    # if there is not an existing owned folder at this path,
                    # create a new folder as a sibling of this not-owned folder
                    yield report.PlanReport(
                        item_action="create-folder",
                        item_type=entry.entry_type,
                        entry_id=entry.entry_id,
                        permission_id=None,
                        description="create an owned folder with same name",
                        begin_user_name=None,
                        begin_user_email=None,
                        begin_user_access=None,
                        begin_entry_name=None,
                        begin_entry_path=None,
                        begin_collection_type=None,
                        begin_collection_name=None,
                        begin_collection_id=None,
                        end_user_name=None,
                        end_user_email=per_account_email,
                        end_user_access=api.role_owner,
                        end_entry_name=entry.name,
                        end_entry_path=parent_path_str,
                        end_collection_type=per_col_type,
                        end_collection_name=per_col_name,
                        end_collection_id=per_col_id,
                    )

                else:
                    # if there is not an existing owned file at this path,
                    # copy the not-owned file
                    yield report.PlanReport(
                        item_action="copy-file",
                        item_type=entry.entry_type,
                        entry_id=entry.entry_id,
                        description="copy file to create a new file owned by the current user",
                        permission_id=None,
                        begin_user_name=None,
                        begin_user_email=None,
                        begin_user_access=None,
                        begin_entry_name=None,
                        begin_entry_path=None,
                        begin_collection_type=None,
                        begin_collection_name=None,
                        begin_collection_id=None,
                        end_user_name=None,
                        end_user_email=per_account_email,
                        end_user_access=api.role_owner,
                        end_entry_name=entry.name,
                        end_entry_path=parent_path_str,
                        end_collection_type=per_col_type,
                        end_collection_name=per_col_name,
                        end_collection_id=per_col_id,
                    )
            else:
                logger.debug(
                    "There is already a copy of the not owned %s '%s' (%s) in '%s'.",
                    entry.entry_type,
                    entry.name,
                    parent_path_str,
                    entry.entry_id,
                    entry_paired.entry_id if entry_paired else "",
                    copy_id,
                )

        # rename
        prefix_copy = per_container.name_prefix_copy_of
        prefix_copy_len = per_container.name_prefix_copy_of_len
        if not entry.is_dir and entry.name and entry.name.startswith(prefix_copy):
            new_name = entry.name[prefix_copy_len:]
            yield report.PlanReport(
                item_action="rename-file",
                item_type=entry.entry_type,
                entry_id=entry.entry_id,
                permission_id=None,
                description="remove 'copy of ' from file name",
                begin_user_name=entry_owner.user_name,
                begin_user_email=entry_owner.user_email,
                begin_user_access=entry_owner.role,
                begin_entry_name=entry.name,
                begin_entry_path=parent_path_str,
                begin_collection_type=per_col_type,
                begin_collection_name=per_col_name,
                begin_collection_id=per_col_id,
                end_user_name=entry_owner.user_name,
                end_user_email=entry_owner.user_email,
                end_user_access=entry_owner.role,
                end_entry_name=new_name,
                end_entry_path=parent_path_str,
                end_collection_type=per_col_type,
                end_collection_name=per_col_name,
                end_collection_id=per_col_id,
            )

        # fix permissions
        for permission in entry.permissions:
            is_owner = permission.role == self._api.role_owner
            is_anyone = permission.entry_type == api.permission_anyone
            is_user = permission.entry_type == api.permission_user
            is_current_user = permission.user_email == per_account_email

            if is_owner or (is_user and is_current_user):
                logger.debug("Keep permission %s.", str(permission))

            elif is_anyone or (is_user and not is_current_user):
                yield report.PlanReport(
                    item_action="delete-permission",
                    item_type=entry.entry_type,
                    entry_id=entry.entry_id,
                    permission_id=permission.entry_id,
                    description="delete permission for non-owner and not current user",
                    begin_user_name=permission.user_name,
                    begin_user_email=permission.user_email,
                    begin_user_access=permission.role,
                    begin_entry_name=entry.name,
                    begin_entry_path=parent_path_str,
                    begin_collection_type=per_col_type,
                    begin_collection_name=per_col_name,
                    begin_collection_id=per_col_id,
                    end_user_name=None,
                    end_user_email=None,
                    end_user_access=None,
                    end_entry_name=None,
                    end_entry_path=None,
                    end_collection_type=None,
                    end_collection_name=None,
                    end_collection_id=None,
                )

            else:
                raise ValueError(f"Unknown permission {str(permission)}.")

        # create an equivalent folder in the business account (only once)
        if entry.is_dir and parent_path_str not in self._bus_folders_path_create:
            self._bus_folders_path_create.append(parent_path_str)
            yield report.PlanReport(
                item_action="create-folder",
                item_type=entry.entry_type,
                entry_id=None,
                permission_id=None,
                description="create same folder in business account",
                begin_user_name=None,
                begin_user_email=None,
                begin_user_access=None,
                begin_entry_name=None,
                begin_entry_path=None,
                begin_collection_type=None,
                begin_collection_name=None,
                begin_collection_id=None,
                end_user_name=None,
                end_user_email=None,
                end_user_access=None,
                end_entry_name=entry.name,
                end_entry_path=parent_path_str,
                end_collection_type=bus_col_type,
                end_collection_name=bus_col_name,
                end_collection_id=bus_col_id,
            )

        if entry.is_dir and parent_path_str in self._bus_folders_path_create:
            logger.debug(
                "Folder in business account already exists or will be created %s.",
                str(entry),
            )

        # transfer ownership of owned files to business account
        # check if not-owned entries have a property indicating the copy has been transferred
        if not per_is_owned and not entry.is_dir:
            # check if the copy of this not-owned entry has already been transferred
            new_account_id = entry.custom_property(config.custom_prop_new_account_key)
            copy_entry_id = entry.custom_property(config.custom_prop_copy_key)
            if not new_account_id:
                yield report.PlanReport(
                    item_action="transfer-owner",
                    item_type=entry.entry_type,
                    entry_id=copy_entry_id,
                    permission_id=None,
                    description="transfer ownership of copied file from personal to business account",
                    begin_user_name=None,
                    begin_user_email=None,
                    begin_user_access=None,
                    begin_entry_name=entry.name,
                    begin_entry_path=parent_path_str,
                    begin_collection_type=per_col_type,
                    begin_collection_name=per_col_name,
                    begin_collection_id=per_col_id,
                    end_user_name=None,
                    end_user_email=None,
                    end_user_access=None,
                    end_entry_name=entry.name,
                    end_entry_path=parent_path_str,
                    end_collection_type=bus_col_type,
                    end_collection_name=bus_col_name,
                    end_collection_id=bus_col_id,
                )

        # transfer any owned files
        if per_is_owned and not entry.is_dir:
            yield report.PlanReport(
                item_action="transfer-ownership",
                item_type=entry.entry_type,
                entry_id=entry.entry_id,
                permission_id=None,
                description="transfer ownership from personal to business account",
                begin_user_name=None,
                begin_user_email=None,
                begin_user_access=None,
                begin_entry_name=entry.name,
                begin_entry_path=parent_path_str,
                begin_collection_type=per_col_type,
                begin_collection_name=per_col_name,
                begin_collection_id=per_col_id,
                end_user_name=None,
                end_user_email=None,
                end_user_access=None,
                end_entry_name=entry.name,
                end_entry_path=parent_path_str,
                end_collection_type=bus_col_type,
                end_collection_name=bus_col_name,
                end_collection_id=bus_col_id,
            )

        if entry.is_dir:
            logger.debug(
                "Can not transfer ownership of folder in personal account %s.",
                str(entry),
            )
