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
        account = config.account

        # report dirs
        plans_dir = config.reports.plans_dir
        outcomes_dir = config.reports.outcomes_dir

        logger.info(
            "Apply modifications for %s account '%s'.",
            account.account_type.name,
            account.account_id,
        )

        # reports
        rpt_plans = report.ReportCsv(plans_dir, report.PlanReport)
        rpt_outcomes = report.ReportCsv(outcomes_dir, report.OutcomeReport)

        plans: typing.Iterable[report.PlanReport] = rpt_plans.read(self._plan_name)

        # read plans and execute
        with rpt_outcomes:
            logger.info("Reading plans report '%s'.", self._plan_name)
            logger.info("Writing outcomes report '%s'.", rpt_outcomes.path.name)

            entry_count = 0

            for index, plan in enumerate(plans):
                entry_count += 1
                self._process_one(rpt_outcomes, plan)

                if self._iteration_check(index):
                    break

            logger.info("Processed total of %s entries.", entry_count)

        logger.info("Finished.")

        return not self._graceful_exit.should_exit()

    def _process_one(
        self,
        rpt_outcomes: report.ReportCsv,
        plan: report.PlanReport,
    ) -> None:
        """Process one entry.

        Args:
            rpt_outcomes: The outcomes report.
            plan: The plan to process.

        Returns:
            None
        """

        rpt_item = self._apply_plan(plan)
        row = dataclasses.asdict(rpt_item)
        rpt_outcomes.write_item(row)

    def _apply_plan(self, plan: report.PlanReport) -> report.OutcomeReport:
        """Execute the actions to apply the plan item."""

        container = self._container
        actions = self._actions

        # properties
        item_action = models.PlanReportActions(plan.item_action)

        # entry
        entry = actions.get_entry(plan.entry_id)

        # outcome
        result_name = "unknown"
        result_description = "The result of applying the plan is not known."
        params = dataclasses.asdict(plan)

        params = {
            **params,
            "result_name": result_name,
            "result_description": result_description,
        }

        # apply plan
        if item_action == models.PlanReportActions.create_folder:
            # check that the action is valid
            self._plan_builder.check_create_folder(entry)

            # TODO: create a folder
            # request = container.create_folder(entry, entry.parent_id)
            # response = container.api.execute_single(request)

            # TODO: build the outcome
            return report.OutcomeReport(**params)

        elif item_action == models.PlanReportActions.copy_file:
            # check that the action is valid
            self._plan_builder.check_copy_file(entry)

            # TODO: copy a file
            # request = container.copy_file(entry, entry.parent_id)
            # response = container.api.execute_single(request)

            # TODO: build the outcome
            return report.OutcomeReport(**params)

        elif item_action == models.PlanReportActions.rename_file:
            # check that the action is valid
            self._plan_builder.check_rename_file(entry)

            # TODO: rename a file
            # request = container.rename_entry(entry, plan.end_entry_name)
            # response = container.api.execute_single(request)

            # TODO: build the outcome
            return report.OutcomeReport(**params)

        elif item_action == models.PlanReportActions.delete_permission:
            # check that the action is valid
            self._plan_builder.check_delete_permission(entry)

            # TODO: delete a permission
            # request = container.delete_permission(plan.permission_id)
            # response = container.api.execute_single(request)

            # TODO: build the outcome
            return report.OutcomeReport(**params)

        elif item_action == models.PlanReportActions.move_entry:
            # check that the action is valid
            self._plan_builder.check_delete_permission(entry)

            # TODO: move a file or folder
            # end_path = plan.end_entry_path
            # end_parent_id = ""
            # request = container.move_file(entry, end_parent_id)
            # response = container.api.execute_single(request)

            # TODO: build the outcome
            return report.OutcomeReport(**params)

        else:
            raise NotImplementedError(f"Plan is not implemented '{plan}'.")
