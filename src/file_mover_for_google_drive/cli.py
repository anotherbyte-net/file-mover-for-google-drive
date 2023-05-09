"""The command line interface."""

import argparse
import logging
import pathlib
import sys
import typing

from file_mover_for_google_drive.actions import show, plan, apply, tidy_properties
from file_mover_for_google_drive.common import models, utils, manage, client


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.INFO)
logging.getLogger("googleapiclient.discovery").setLevel(logging.INFO)
logging.getLogger("google_auth_oauthlib.flow").setLevel(logging.INFO)
logging.getLogger("requests_oauthlib.oauth2_session").setLevel(logging.INFO)
logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)


def run_cli(
    args: argparse.Namespace, gd_client: typing.Optional[client.GoogleApiClient] = None
) -> int:
    """Run the cli.

    Args:
        args: The parsed arguments.
        gd_client: The Google Drive client. Used for testing.

    Returns:
        Program exit code.
    """

    def _get_arg(args1: argparse.Namespace, name: str) -> typing.Optional[typing.Any]:
        """Get the property with name from args1.

        Args:
            args1: The parsed arguments.
            name: The property name.

        Returns:
            The property value or None if not found.
        """

        return getattr(args1, name) if hasattr(args, name) else None

    def _get_path(
        args1: argparse.Namespace, name: str
    ) -> typing.Optional[pathlib.Path]:
        """Get the path property with name from args1.

        Args:
            args1: The parsed arguments.
            name: The property name.

        Returns:
            The value as a path or None if not found.
        """

        value = _get_arg(args1, name)
        return pathlib.Path(value) if value else None

    config_file = _get_path(args, "config_file")
    plan_name = _get_arg(args, "plan-name") or _get_arg(args, "plan_name")
    subparser_name = _get_arg(args, "subparser_name")

    if not config_file:
        raise ValueError("Must provide config file.")

    config = models.ConfigProgram.load_file(config_file)

    manage_item: manage.BaseManage

    if subparser_name == "show":
        manage_item = show.Show(config=config, gd_client=gd_client)

    elif subparser_name == "plan":
        manage_item = plan.Plan(config=config, gd_client=gd_client)

    elif subparser_name == "apply":
        manage_item = apply.Apply(
            plan_name=plan_name, config=config, gd_client=gd_client
        )

    elif subparser_name == "tidy-properties":
        manage_item = tidy_properties.TidyProperties(config=config, gd_client=gd_client)

    else:
        raise ValueError(f"Unknown activity '{subparser_name}'.")

    result = manage_item.run()

    return 0 if result else 1


def main(
    args: typing.Optional[list[str]] = None,
    gd_client: typing.Optional[client.GoogleApiClient] = None,
) -> int:
    """The program entry point.

    Args:
        args: The raw program arguments.
        gd_client: A Google Drive client. Used for testing.

    Returns:
        Program exit code.
    """

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
        "plan-name",
        help="The name of the plan file to apply (without the .csv extension).",
    )
    parser_apply.set_defaults(func=run_cli)

    # create the parser for the "tidy-properties" command
    parser_plan = subparsers.add_parser(
        "tidy-properties",
        description="Tidy entry properties.",
        help="Tidy entry properties.",
    )
    _add_config_file_arg(parser_plan)
    parser_plan.set_defaults(func=run_cli)

    # parse args
    parsed_args = parser.parse_args(args)

    if not parsed_args.subparser_name:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # execute
    exit_code = parsed_args.func(parsed_args, gd_client)

    if not isinstance(exit_code, int):
        raise ValueError(f"Invalid exit code '{exit_code}'.")

    # return exit code
    return exit_code


def _add_config_file_arg(parser: argparse.ArgumentParser) -> None:
    """Add the config argument.

    Args:
        parser: The argument parser.

    Returns:
        None
    """

    parser.add_argument(
        "--config-file",
        help="The path to the config file.",
    )


if __name__ == "__main__":
    sys.exit(main())
