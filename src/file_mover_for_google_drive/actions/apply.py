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
        gd_client: typing.Optional[client.GoogleApiClient] = None,
    ) -> None:
        """Create a new Apply instance."""

        super().__init__(config=config, allow_modify=True, gd_client=gd_client)

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
                self.process_one(rpt_outcomes, plan)

                if self._iteration_check(index):
                    break

            logger.info("Processed total of %s entries.", entry_count)

        logger.info("Finished.")

        return not self._graceful_exit.should_exit()

    def process_one(
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

        logger.info(f"==> Outcome: {str(rpt_item)}.")

        row = dataclasses.asdict(rpt_item)
        row["result_name"] = row["result_name"].name
        rpt_outcomes.write_item(row)

    def _apply_plan(self, plan: report.PlanReport) -> report.OutcomeReport:
        """Execute the actions to apply the plan item."""

        actions = self._actions

        # properties
        item_action = models.PlanReportActions(plan.item_action)

        # entry
        if not plan.entry_id:
            raise ValueError("Require a valid entry id to apply a plan item.")
        entry = actions.get_entry(plan.entry_id)

        # outcome
        result_name = models.PlanReportOutcomes.UNKNOWN
        result_description = "The result of applying the plan is not known."
        params = dataclasses.asdict(plan)

        params = {
            **params,
            "result_name": result_name,
            "result_description": result_description,
        }

        logger.info(f"Applying plan {str(plan)}.")

        # apply plan
        if item_action == models.PlanReportActions.CREATE_FOLDER:
            return self._apply_create_folder(params, entry)

        if item_action == models.PlanReportActions.COPY_FILE:
            return self._apply_copy_file(params, entry)

        if item_action == models.PlanReportActions.RENAME_FILE:
            return self._apply_rename_file(params, entry, plan)

        if item_action == models.PlanReportActions.DELETE_PERMISSION:
            return self._apply_delete_permission(params, entry, plan)

        if item_action == models.PlanReportActions.MOVE_ENTRY:
            return self._apply_move_entry(params, entry, plan)

        raise ValueError(f"Plan is not implemented '{plan}'.")

    def _apply_create_folder(self, params, entry):
        actions = self._actions
        actions_config = self._config.actions

        # Check that action is permitted
        if not actions_config.create_owned_folder_and_move_contents:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        # check that the action is valid
        self._plan_builder.check_create_folder(entry)

        # check that the folder doesn't already exist
        entry_other = actions.get_pair_copy_entry(entry)
        if entry_other:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Folder already exists: "
                    f"{str(entry_other)}.",
                }
            )

        # execute the plan
        new_entry, entry = actions.create_folder(entry)

        # report the outcome
        return report.OutcomeReport(
            **{
                **params,
                "result_name": models.PlanReportOutcomes.SUCCESS,
                "result_description": f"Created new folder '{new_entry.name}' "
                f"({new_entry.entry_id})",
            }
        )

    def _apply_copy_file(self, params, entry):
        actions = self._actions
        actions_config = self._config.actions

        # Check that action is permitted
        if not actions_config.create_owned_file_copy:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        # check that the action is valid
        self._plan_builder.check_copy_file(entry)

        # check that the copy doesn't already exist
        entry_other = actions.get_pair_copy_entry(entry)
        if entry_other:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": f"File already exists: {str(entry_other)}.",
                }
            )

        # execute the plan
        new_entry, entry = actions.copy_file(entry)

        # report the outcome
        return report.OutcomeReport(
            **{
                **params,
                "result_name": models.PlanReportOutcomes.SUCCESS,
                "result_description": f"Copied file '{new_entry.name}' "
                f"to create new file with id {new_entry.entry_id}",
            }
        )

    def _apply_rename_file(self, params, entry, plan):
        actions = self._actions
        actions_config = self._config.actions

        # Check that action is permitted
        if not actions_config.entry_name_delete_prefix_copy_of:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        # check that the action is valid
        self._plan_builder.check_rename_file(entry)

        # check that the rename is required
        if entry.name == plan.end_entry_name:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "File name is already as expected.",
                }
            )

        # execute the plan
        new_entry = actions.rename_entry(entry, plan.end_entry_name)

        # report the outcome
        return report.OutcomeReport(
            **{
                **params,
                "result_name": models.PlanReportOutcomes.SUCCESS,
                "result_description": f"Renamed file from '{entry.name}' "
                f"to {new_entry.name}",
            }
        )

    def _apply_delete_permission(self, params, entry, plan):
        actions = self._actions
        actions_config = self._config.actions

        # get the permission object
        permission: typing.Optional[models.GoogleDrivePermission] = None
        for item in entry.permissions_all:
            if item.entry_id == plan.permission_id:
                permission = item
                break

        # check that the permission exists
        if not permission:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "The permission does not exist.",
                }
            )

        # check that the action is valid
        self._plan_builder.check_delete_permission(permission)

        # Check that action is permitted
        # Note that this needs to differentiate between permission types
        permission_anyone = models.GoogleDrivePermissionTypeOptions.ANYONE
        if (
            permission.entry_type == permission_anyone
            and not actions_config.permissions_delete_link
        ):
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        if (
            permission.entry_type != permission_anyone
            and not actions_config.permissions_delete_other_users
        ):
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        if (
            plan.begin_user_email in actions_config.permissions_user_emails_keep
            or plan.end_user_email in actions_config.permissions_user_emails_keep
        ):
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        # execute the plan
        actions.delete_permission(plan.entry_id, plan.permission_id)

        # report the outcome
        return report.OutcomeReport(
            **{
                **params,
                "result_name": models.PlanReportOutcomes.SUCCESS,
                "result_description": f"Deleted permission id '{plan.permission_id}' "
                f"from entry id '{plan.entry_id}'",
            }
        )

    def _apply_move_entry(self, params, entry, plan):
        actions = self._actions
        config = self._config

        actions_config = config.actions
        account = config.account
        account_id = account.account_id

        # Check that action is permitted
        if not actions_config.create_owned_folder_and_move_contents:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "Config prevented executing plan action",
                }
            )

        # check that the action is valid
        self._plan_builder.check_move_entry()

        # get the new parent folder id
        entry_parent = actions.get_entry(entry.parent_id)
        entry_parent_other = actions.get_pair_copy_entry(entry_parent)
        if not entry_parent_other:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.FAILED,
                    "result_description": "Could not find "
                    f"owned folder '{plan.end_entry_path}'.",
                }
            )

        if not entry_parent_other.is_copy:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "The found folder is not an owned copy "
                    "(this could mean the move was already done): "
                    f" {str(entry_parent_other)}.",
                }
            )

        if not entry_parent_other.is_dir:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.FAILED,
                    "result_description": "The found entry is not a folder: "
                    f" {str(entry_parent_other)}.",
                }
            )

        # if the entry is an unowned original, move the copy instead
        if not entry.is_owned_by(account_id):
            to_move = actions.get_pair_copy_entry(entry)
            if not to_move:
                return report.OutcomeReport(
                    **{
                        **params,
                        "result_name": models.PlanReportOutcomes.FAILED,
                        "result_description": "There is no owned copy of the file. "
                        "Check the order of the plans.",
                    }
                )
        else:
            to_move = entry

        # check that the file needs to be moved
        if to_move.parent_id == entry_parent_other.entry_id:
            return report.OutcomeReport(
                **{
                    **params,
                    "result_name": models.PlanReportOutcomes.SKIPPED,
                    "result_description": "The file is already in the expected folder.",
                }
            )

        # execute the plan
        new_entry = actions.move_entry(to_move, entry_parent_other.entry_id)

        # report the outcome
        return report.OutcomeReport(
            **{
                **params,
                "result_name": models.PlanReportOutcomes.SUCCESS,
                "result_description": "Move file into folder "
                f"with id '{new_entry.parent_id}'.",
            }
        )
