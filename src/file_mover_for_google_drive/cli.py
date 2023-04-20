"""The command line interface."""

import argparse
import logging
import pathlib
import sys
import typing

from file_mover_for_google_drive.actions import show, plan, apply
from file_mover_for_google_drive.common import models, utils, manage

log_level = logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)-8s] [%(name)s] %(message)s",
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(log_level)
logging.getLogger("googleapiclient.discovery").setLevel(log_level)


def run_cli(args, client=None) -> int:
    """Run the cli."""

    def _get_arg(args1, name: str):
        """Get the property with name from args1."""

        return getattr(args1, name) if hasattr(args, name) else None

    def _get_path(args1, name) -> typing.Optional[pathlib.Path]:
        """Get the path property with name from args1."""

        value = _get_arg(args1, name)
        return pathlib.Path(value) if value else None

    account = _get_arg(args, "account")
    config_file = _get_path(args, "config_file")
    plan_file = _get_path(args, "plan-file") or _get_path(args, "plan_file")
    subparser_name = _get_arg(args, "subparser_name")

    if not config_file:
        raise ValueError("Must provide config file.")

    config = models.Config.load(config_file)

    manage_item: manage.BaseManage

    if subparser_name == "show":
        manage_item = show.Show(account, config, client)
    elif subparser_name == "plan":
        manage_item = plan.Plan(config, client)
    elif subparser_name == "apply":
        manage_item = apply.Apply(plan_file, config, client)
    else:
        raise ValueError(f"Unknown activity '{subparser_name}'.")

    result = manage_item.run()

    return 0 if result else 1


def main(args=None, client=None) -> int:
    """The program entry point."""

    if args is None:
        args = sys.argv[1:]

    # create the top-level parser
    parser = argparse.ArgumentParser(
        prog=utils.get_name_dash(), description=utils.get_prog_description()
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {utils.get_version()}",
    )
    parser.set_defaults(func=run_cli)
    subparsers = parser.add_subparsers(dest="subparser_name", help="sub-command help")

    # create the parser for the "show" command
    parser_show = subparsers.add_parser(
        "show",
        description="Show the files, folders, and permissions in a Google Drive.",
        help="Show the files, folders, and permissions in a Google Drive.",
    )
    _add_config_file_arg(parser_show)
    parser_show.add_argument(
        "account",
        choices=["personal", "business"],
        help="Chose either the personal or business accounts from the config file.",
    )
    parser_show.set_defaults(func=run_cli)

    # create the parser for the "plan" command
    parser_plan = subparsers.add_parser(
        "plan",
        description="Build a plan of the changes.",
        help="Build a plan of the changes.",
    )
    _add_config_file_arg(parser_plan)
    parser_plan.set_defaults(func=run_cli)

    # create the parser for the "apply" command
    parser_apply = subparsers.add_parser(
        "apply",
        description="Apply changes from a plan file.",
        help="Apply changes from a plan file.",
    )
    _add_config_file_arg(parser_apply)
    parser_apply.add_argument(
        "plan-file",
        help="The path to the plan file to apply.",
    )
    parser_apply.set_defaults(func=run_cli)

    # parse args
    parsed_args = parser.parse_args(args)

    if not parsed_args.subparser_name:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # execute
    exit_code = parsed_args.func(parsed_args, client)

    # return exit code
    return exit_code


def _add_config_file_arg(parser):
    """Add the config argument."""

    parser.add_argument(
        "--config-file",
        help="The path to the config file.",
    )


if __name__ == "__main__":
    sys.exit(main())
