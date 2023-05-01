"""The apply action."""

import dataclasses
import logging
import typing

from file_mover_for_google_drive.common import manage, models, report, client

logger = logging.getLogger(__name__)


class Apply(manage.BaseManage):
    """Action the changes described in a previously generated plan."""

    def __init__(
        self,
        plan_name: typing.Optional[str],
        config: models.ConfigProgram,
        gd_client: client.GoogleApiClient = None,
    ) -> None:
        """Create a new Apply instance."""

        super().__init__(config, gd_client)

        if not plan_name:
            raise ValueError("Must provide plan path.")

        self._plan_name = plan_name

    def run(self) -> bool:
        """
        Run the 'apply' action.

        Returns:
            The outcome of the action.
        """

        config = self._config
        container = self._container
        actions = self._actions
        cache = self._cache

        top_folder_id = config.account.top_folder_id
        account = config.account

        # report dirs
        entries_dir = config.reports.entries_dir
        perms_dir = config.reports.permissions_dir
        plans_dir = config.reports.plans_dir
        outcomes_dir = config.reports.outcomes_dir

        logger.info(
            "Apply modifications for %s account '%s'.",
            account.account_type.name,
            account.account_id,
        )

        # reports
        rpt_entries = report.ReportCsv(entries_dir, report.EntryReport)
        rpt_permissions = report.ReportCsv(perms_dir, report.PermissionReport)
        rpt_plans = report.ReportCsv(plans_dir, report.PlanReport)
        rpt_outcomes = report.ReportCsv(outcomes_dir, report.OutcomeReport)

        plans: list[report.PlanReport] = list(rpt_plans.read(self._plan_name))

        # read plans and execute
        with rpt_entries, rpt_permissions, rpt_outcomes:
            logger.info("Reading plans report '%s'.", self._plan_name)
            logger.info("Writing entries report '%s'.", rpt_entries.path.name)
            logger.info("Writing permissions report '%s'.", rpt_permissions.path.name)
            logger.info("Writing outcomes report '%s'.", rpt_outcomes.path.name)

            entry_count = 0

            # top entry
            top_entry = actions.get_entry(top_folder_id)
            entry_count += 1
            self._process_one(
                rpt_entries,
                rpt_permissions,
                rpt_outcomes,
                plans,
                top_entry,
            )

            logger.info("Starting folder is '%s'.", top_entry.name)

            # descendants
            descendants = actions.get_descendants(top_folder_id)
            for index, entry in enumerate(descendants):
                entry_count += 1

                self._process_one(
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
        rpt_entries: report.ReportCsv,
        rpt_permissions: report.ReportCsv,
        rpt_outcomes: report.ReportCsv,
        plans: list[report.PlanReport],
        entry: models.GoogleDriveEntry,
    ) -> None:
        """Process one entry.

        Args:
            rpt_entries: The entries report.
            rpt_permissions: The permissions report.
            rpt_outcomes: The outcomes report.
            plans: The plans to process.
            entry: Apply the plans to this entry.

        Returns:
            None
        """
        config = self._config
        container = self._container
        actions = self._actions
        cache = self._cache

        top_folder_id = config.account.top_folder_id
        account = config.account

        cache.add(entry)

        entry_path = cache.path(entry.entry_id)

        for row in report.EntryReport.from_entry_path(entry_path):
            rpt_entries.write_item(row)

        for row in report.PermissionReport.from_entry_path(entry_path):
            rpt_permissions.write_item(row)

        for rpt_item in self._apply_plans(plans, entry_path):
            row = dataclasses.asdict(rpt_item)
            rpt_outcomes.write_item(row)

    def _apply_plans(
        self,
        plans: list[report.PlanReport],
        entry_path: list[models.GoogleDriveEntry],
    ) -> typing.Iterable[report.OutcomeReport]:
        """Apply plan items to enact planned changes."""

        config = self._config
        container = self._container
        actions = self._actions
        cache = self._cache

        top_folder_id = config.account.top_folder_id
        account = config.account

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
            for item in self._apply_plan(plan, entry_path):
                yield item

    def _apply_plan(
        self,
        plan: report.PlanReport,
        entry_path: list[models.GoogleDriveEntry],
    ) -> typing.Iterable[report.OutcomeReport]:
        """Execute the actions to apply the plan item."""

        config = self._config
        container = self._container
        actions = self._actions
        cache = self._cache

        top_folder_id = config.account.top_folder_id
        account = config.account

        # entry = entry_path[-1]
        # parent_path_str = entry.build_path_str(entry_path[:-1])

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

        # end_user_name = plan.end_user_name
        # end_user_email = plan.end_user_email
        # end_user_access = plan.end_user_access
        # end_entry_name = plan.end_entry_name
        # end_entry_path = plan.end_entry_path

        params = dataclasses.asdict(plan)

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

        else:
            raise ValueError(f"Unknown plan '{plan}'.")
