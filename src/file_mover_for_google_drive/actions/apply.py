"""The apply action."""

import dataclasses
import logging
import pathlib
import typing

from file_mover_for_google_drive.common import (
    manage,
    models,
    interact,
    utils,
    report,
    client,
)

logger = logging.getLogger(__name__)


class Apply(manage.BaseManage):
    """Action the changes described in a previously generated plan."""

    def __init__(
        self,
        plan_path: typing.Optional[pathlib.Path],
        config: models.Config,
        gd_client: client.GoogleDriveAnyClientType = None,
    ) -> None:
        """Create a new Apply instance."""

        super().__init__(config, gd_client)

        if not plan_path:
            raise ValueError("Must provide plan path.")

        self._plan_path = plan_path

    def run(self) -> bool:
        """
        Run the 'apply' action.

        Returns:
            The outcome of the action.
        """

        config = self._config

        # personal
        per_container = self._personal_container
        per_actions = interact.GoogleDriveActions(per_container)
        per_top_folder_id = config.personal_account_top_folder_id
        per_cache = utils.GoogleDriveEntryCache(per_top_folder_id)
        per_col_type = per_container.collection_type
        per_col_name = per_container.collection_name
        per_col_id = per_container.collection_id

        # business
        bus_container = self._business_container
        # bus_actions = interact.GoogleDriveActions(bus_container)
        bus_top_folder_id = config.business_account_top_folder_id
        bus_cache = utils.GoogleDriveEntryCache(bus_top_folder_id)
        bus_col_type = bus_container.collection_type
        bus_col_name = bus_container.collection_name
        bus_col_id = bus_container.collection_id

        # report dirs
        entries_dir = config.report_entries_dir
        perms_dir = config.report_permissions_dir
        outcomes_dir = config.report_outcomes_dir

        logger.info(
            "Apply modifications for '%s' in %s '%s'.",
            per_col_name,
            per_col_type,
            per_col_id,
        )
        logger.info("Starting with folder '%s'.", per_top_folder_id)
        logger.info(
            "Move files and folders to '%s' in %s '%s'.",
            bus_col_name,
            bus_col_type,
            bus_col_id,
        )
        logger.info("Moving into top folder '%s'.", bus_top_folder_id)

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(perms_dir, report.PermissionReport)
        rpt_outcomes = report.ReportCsv(outcomes_dir, report.OutcomeReport)

        plans = list(report.PlanReport.from_path(self._plan_path))

        # read plans and execute
        with rpt_entries, rpt_permissions, rpt_outcomes:
            logger.info("Reading plans report '%s'.", self._plan_path.name)
            logger.info("Writing entries report '%s'.", rpt_entries.path.name)
            logger.info("Writing permissions report '%s'.", rpt_permissions.path.name)
            logger.info("Writing outcomes report '%s'.", rpt_outcomes.path.name)

            logger.info("Starting.")

            entry_count = 0

            # top entry
            per_top_entry = per_actions.get_entry(per_top_folder_id)
            entry_count += 1
            self._process_one(
                per_cache,
                bus_cache,
                rpt_entries,
                rpt_permissions,
                rpt_outcomes,
                plans,
                per_top_entry,
            )

            # descendants
            descendants = per_actions.get_descendants(per_top_folder_id)
            for index, entry in enumerate(descendants):
                entry_count += 1

                self._process_one(
                    per_cache,
                    bus_cache,
                    rpt_entries,
                    rpt_permissions,
                    rpt_outcomes,
                    plans,
                    entry,
                )

                if self._iteration_check(index):
                    break

            logger.info("Processed total of %s entries.", entry_count)

        logger.info("Finished.")

        return not self._graceful_exit.should_exit()

    def _process_one(
        self,
        per_cache: utils.GoogleDriveEntryCache,
        bus_cache: utils.GoogleDriveEntryCache,
        rpt_entries: report.ReportCsv,
        rpt_permissions: report.ReportCsv,
        rpt_outcomes: report.ReportCsv,
        plans: list[report.PlanReport],
        entry: models.GoogleDriveEntry,
    ) -> None:
        """Process one entry.

        Args:
            per_cache: The personal data cache.
            bus_cache: The business data cache.
            rpt_entries: The entries report.
            rpt_permissions: The permissions report.
            rpt_outcomes: The outcomes report.
            plans: The plans to process.
            entry: Apply the plans to this entry.

        Returns:
            None
        """
        per_cache.add(entry)

        entry_path = per_cache.path(entry.entry_id)

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)

        for rpt_item in self._apply_plans(per_cache, bus_cache, plans, entry_path):
            row = dataclasses.asdict(rpt_item)
            rpt_outcomes.write_item(row)

    def _apply_plans(
        self,
        per_cache: utils.GoogleDriveEntryCache,
        bus_cache: utils.GoogleDriveEntryCache,
        plans: list[report.PlanReport],
        entry_path: list[models.GoogleDriveEntry],
    ) -> typing.Iterable[report.OutcomeReport]:
        """Apply plan items to enact planned changes."""

        entry = entry_path[-1]
        parent_path_str = entry.build_path_str(entry_path[:-1])

        # action all the plans that apply to this entry

        for plan in plans:
            if plan.entry_id and plan.entry_id != entry.entry_id:
                continue
            if plan.begin_entry_path and plan.begin_entry_path != parent_path_str:
                continue
            if plan.end_entry_path and plan.end_entry_path != parent_path_str:
                continue
            for item in self._apply_plan(per_cache, bus_cache, plan, entry_path):
                yield item

    def _apply_plan(
        self,
        per_cache: utils.GoogleDriveEntryCache,
        bus_cache: utils.GoogleDriveEntryCache,
        plan: report.PlanReport,
        entry_path: list[models.GoogleDriveEntry],
    ) -> typing.Iterable[report.OutcomeReport]:
        """Execute the actions to apply the plan item."""

        # entry = entry_path[-1]
        # parent_path_str = entry.build_path_str(entry_path[:-1])

        per_container = self._personal_container
        # per_actions = interact.GoogleDriveActions(per_container)

        bus_container = self._business_container
        # bus_actions = interact.GoogleDriveActions(bus_container)

        # properties
        item_action = plan.item_action
        # item_type = plan.item_type
        # entry_id = plan.entry_id
        # permission_id = plan.permission_id

        # begin_user_name = plan.begin_user_name
        # begin_user_email = plan.begin_user_email
        # begin_user_access = plan.begin_user_access
        # begin_entry_name = plan.begin_entry_name
        # begin_entry_path = plan.begin_entry_path
        # begin_collection_type = plan.begin_collection_type
        # begin_collection_name = plan.begin_collection_name
        # begin_collection_id = plan.begin_collection_id

        # end_user_name = plan.end_user_name
        # end_user_email = plan.end_user_email
        # end_user_access = plan.end_user_access
        # end_entry_name = plan.end_entry_name
        # end_entry_path = plan.end_entry_path
        end_collection_type = plan.end_collection_type
        # end_collection_name = plan.end_collection_name
        # end_collection_id = plan.end_collection_id

        params = dataclasses.asdict(plan)

        # per_begin = begin_collection_type == per_container.collection_type
        # bus_begin = begin_collection_type == bus_container.collection_type
        per_end = end_collection_type == per_container.collection_type
        bus_end = end_collection_type == bus_container.collection_type

        # apply plan
        if item_action == "create":
            # create a file or folder or permission
            # creating a folder involves creating all the parent folders as well
            # ignore 'begin_*' properties
            # full_path = end_entry_path.split("/") + [end_entry_name]
            if per_end:
                pass
            elif bus_end:
                pass
            yield report.OutcomeReport(result_name="skipped", **params)

        elif item_action == "copy":
            # copy a file
            yield report.OutcomeReport(result_name="skipped", **params)

        elif item_action == "update":
            # update a file or folder properties
            yield report.OutcomeReport(result_name="skipped", **params)

        elif item_action == "delete":
            # delete a permission
            yield report.OutcomeReport(result_name="skipped", **params)

        elif item_action == "transfer":
            # transfer ownership of a file
            yield report.OutcomeReport(result_name="skipped", **params)

        else:
            raise ValueError(f"Unknown plan '{plan}'.")
