"""CLI functions.
"""

import os
import argparse
import coloredlogs
import datetime
import logging
import sys
import json
import operator

from zoneinfo import ZoneInfo

import ace_api

from ace_hunter import Hunter
from ace_hunter.query_hunter import QueryHunt
from ace_hunter.config import CONFIG, LOCAL_TIMEZONE, event_time_format_tz
from ace_hunter.util import create_timedelta

LOGGER = logging.getLogger("ace_hunter.cli")


def list_hunt_types(args):
    hunter = Hunter()
    if not hunter.load_hunt_managers():
        LOGGER.warning("no hunt type managers loaded.")
        return False
    LOGGER.debug("listing hunt types...")
    print("Hunt Types:")
    for hunt_type in hunter.hunt_managers.keys():
        print(f"\t{hunt_type}")
    return True


def list_hunts(args):
    hunter = Hunter()
    if not hunter.load_hunt_managers():
        LOGGER.warning("no hunt type managers loaded.")
        return False
    LOGGER.debug("listing hunts...")
    print("Hunts:")
    for hunt_type, manager in sorted(hunter.hunt_managers.items()):
        manager.load_hunts_from_config()
        for hunt in sorted(
            sorted(manager.hunts, key=operator.attrgetter("name")), key=operator.attrgetter("enabled"), reverse=True
        ):
            ini_file = os.path.splitext(os.path.basename(hunt.ini_path))[0]
            status = "E" if hunt.enabled else "D"
            print(f"\t{status} {hunt_type}:{ini_file} - {hunt.name}")

    return True


def verify_hunts(args):
    hunter = Hunter()
    hunter.load_hunt_managers()
    failed = False
    for hunt_type, manager in hunter.hunt_managers.items():
        manager.load_hunts_from_config()
        if manager.failed_ini_files:
            LOGGER.error(
                f"unable to load {len(manager.failed_ini_files)} out of {len(manager._list_hunt_ini())} {hunt_type} hunts\n"
            )
            failed = True

    if failed:
        return False

    LOGGER.info("hunt syntax verified")
    print("hunt syntax verified")
    return True


def execute_hunt(args):
    hunter = Hunter()
    hunter.load_hunt_managers()

    hunt_type, hunt_name = args.hunt.split(":", 1)
    if hunt_type not in hunter.hunt_managers:
        LOGGER.error(f"invalid or miss-configured hunt type {hunt_type}")
        return False

    hunter.hunt_managers[hunt_type].load_hunts_from_config()
    hunt = hunter.hunt_managers[hunt_type].get_hunt(lambda hunt: hunt_name in hunt.ini_path)
    if hunt is None:
        LOGGER.error(f"unknown hunt {hunt_name} for type {hunt_type}")
        return False

    # set the Hunt to manual so we don't record the execution timestamps
    hunt.manual_hunt = True
    exec_kwargs = {}

    if isinstance(hunt, QueryHunt):
        start_time = datetime.datetime.strptime(args.start_time, "%m/%d/%Y:%H:%M:%S")
        end_time = datetime.datetime.strptime(args.end_time, "%m/%d/%Y:%H:%M:%S")

        timezone = LOCAL_TIMEZONE
        if args.timezone is not None:
            timezone = ZoneInfo(args.timezone)

        start_time = start_time.replace(tzinfo=timezone)
        end_time = end_time.replace(tzinfo=timezone)

        if args.relative_start_time is not None:
            start_time = datetime.datetime.now() - create_timedelta(args.relative_start_time)
        if args.relative_end_time is not None:
            end_time = datetime.datetime.now() - create_timedelta(args.relative_end_time)

        exec_kwargs["start_time"] = start_time
        exec_kwargs["end_time"] = end_time

        hunt.query_result_file = args.query_result_file

    if args.json_dir is not None:
        os.makedirs(args.json_dir, exist_ok=True)

    json_dir_index = 0
    for submission in hunt.execute(**exec_kwargs):
        LOGGER.info(f"{submission.description} - {submission.analysis_mode}")
        if args.details:
            for o in submission.observables:
                output = f"\t(*) {o['type']} - {o['value']}"
                if "time" in o:
                    output += " - {}".format(o["time"].strftime(event_time_format_tz))
                if "tags" in o:
                    output += " tags [{}]".format(",".join(o["tags"]))
                if "directives" in o:
                    output += " direc [{}]".format(",".join(o["directives"]))
                # TODO the other stuff
                print(output)

            for t in submission.tags:
                print(f"\t(+) {t}")

        if args.events:
            LOGGER.info("BEGIN EVENTS")
            for event in submission.details:
                print(json.dumps(event, indent=1))
            LOGGER.info("END EVENTS")

        if args.json_dir is not None:
            buffer = []
            for event in submission.details:
                buffer.append(event)

            target_json_file = os.path.join(args.json_dir, "{}.json".format(str(json_dir_index)))
            with open(target_json_file, "w") as fp:
                json.dump(buffer, fp)

            with open(os.path.join(args.json_dir, "manifest"), "a") as fp:
                fp.write(f"{json_dir_index} = {submission.description}\n")

            json_dir_index += 1

        ssl_verification = CONFIG["SSL"]["ca_chain_path"]
        if not os.path.exists(ssl_verification):
            ssl_verification = CONFIG["SSL"].getboolean("verify_ssl", True)

        if args.submit_alerts is not None:
            result = ace_api.submit(
                submission.description,
                remote_host=args.submit_alerts,
                ssl_verification=ssl_verification,
                analysis_mode=submission.analysis_mode,
                tool=submission.tool,
                tool_instance=submission.tool_instance,
                type=submission.type,
                event_time=submission.event_time,
                details=submission.details,
                observables=submission.observables,
                tags=submission.tags,
                # TODO: update ace_api pypi lib.
                # queue=submission.queue,
                # instructions=submission.instructions,
                files=[],
            )
            if result:
                LOGGER.info(
                    f"  + Got submission UUID={result['result']['uuid']} from {args.submit_alerts} for {submission.description}"
                )


def config_query(args):
    from ace_hunter.config import CONFIG

    def matches_param(s, k=None):
        if not args.settings:
            return True

        for spec in args.settings:
            section_spec, key_spec = spec.split(".")
            # print("testing {} == {} {} == {}".format(section_spec, s, key_spec, k))
            if (section_spec == "*" or section_spec == s) and (k is None or key_spec == "*" or key_spec == k):
                return True

        return False

    for section in list(CONFIG.keys()):
        if section == "DEFAULT":
            continue

        if not matches_param(section):
            continue

        if not args.value_only:
            print("[{}]".format(section))

        for key in CONFIG[section].keys():
            if not matches_param(section, key):
                continue

            if args.value_only:
                print(CONFIG[section][key])
            else:
                print("{} = {}".format(key, CONFIG[section][key]))

        if not args.value_only:
            print()

    return True


def configure(args):
    """Add items to the user level configuration file."""
    import getpass
    from ace_hunter.config import save_config_item

    section, key = args.setting.split(".")
    if not section and key:
        return False

    if not args.value:
        if args.value_prompt or key.startswith("pass"):
            args.value = getpass.getpass(f"Enter value for {section}.{key}: ")
        else:
            args.value = input(f"Enter value for {section}.{key}: ")

    return save_config_item(section, key, args.value)


def build_parser(parser: argparse.ArgumentParser):
    """Build the CLI Argument parser."""

    parser.add_argument("-d", "--debug", default=False, action="store_true", help="Turn on debug logging.")

    subparsers = parser.add_subparsers(dest="command")

    list_types_parser = subparsers.add_parser("list-types", aliases=["lt"], help="List the types of Hunts configured.")
    list_types_parser.set_defaults(func=list_hunt_types)

    list_hunts_parser = subparsers.add_parser(
        "list",
        aliases=["l"],
        help="""List the available hunts.
        The format of the output is
        E|D type:name - description
        E: enabled
        D: disabled""",
    )
    list_hunts_parser.set_defaults(func=list_hunts)

    verify_hunt_parser = subparsers.add_parser(
        "verify", aliases=["v"], help="Verifies that all configured hunts are able to load."
    )
    verify_hunt_parser.set_defaults(func=verify_hunts)

    execute_hunt_parser = subparsers.add_parser(
        "execute", aliases=["e"], help="Execute a hunt with the given parameters."
    )
    execute_hunt_parser.add_argument(
        "hunt", help="The name of the hunt to execute in the format type:name where type is the hunt type."
    )
    default_start_time = datetime.datetime.now() - datetime.timedelta(hours=24)
    default_start_time = default_start_time.strftime("%m/%d/%Y:%H:%M:%S")
    execute_hunt_parser.add_argument(
        "-s",
        "--start-time",
        required=False,
        default=default_start_time,
        help="Optional start time. Time spec absolute format is MM/DD/YYYY:HH:MM:SS. Default=24 hours ago",
    )
    default_end_time = datetime.datetime.now().strftime("%m/%d/%Y:%H:%M:%S")
    execute_hunt_parser.add_argument(
        "-e",
        "--end-time",
        required=False,
        default=default_end_time,
        help="Optional end time. Time spec absolute format is MM/DD/YYYY:HH:MM:SS",
    )
    execute_hunt_parser.add_argument(
        "-S",
        "--relative-start-time",
        required=False,
        default=None,
        dest="relative_start_time",
        help="Specify the starting time as a time relative to now in DD:HH:MM:SS format.",
    )
    execute_hunt_parser.add_argument(
        "-E",
        "--relative-end-time",
        required=False,
        default=None,
        dest="relative_end_time",
        help="Specify the ending time as a time relative to now in DD:HH:MM:SS format.",
    )
    execute_hunt_parser.add_argument(
        "-z",
        "--timezone",
        required=False,
        default=None,
        help="Optional time zone for start time and end time. Defaults to local time zone.",
    )
    execute_hunt_parser.add_argument(
        "-v",
        "--events",
        required=False,
        default=False,
        action="store_true",
        help="Output the events instead of the submissions.",
    )
    execute_hunt_parser.add_argument(
        "--json-dir",
        required=False,
        default=None,
        help="Store the events as JSON files in the given directory, one per submission created.",
    )
    execute_hunt_parser.add_argument(
        "-d",
        "--details",
        required=False,
        default=False,
        action="store_true",
        help="Include the details of the submissions in the output.",
    )
    execute_hunt_parser.add_argument(
        "--submit-alerts", required=False, default=None, help="Submit as alerts to the given host[:port]"
    )
    execute_hunt_parser.add_argument(
        "--query-result-file",
        required=False,
        default=None,
        help="Valid only for query hunts. Save the raw query results to the given file.",
    )
    execute_hunt_parser.set_defaults(func=execute_hunt)

    config_parser = subparsers.add_parser("config-query", aliases=["cq"], help="Query the Hunter configuration.")
    config_parser.add_argument(
        "-v",
        "--value",
        action="store_true",
        default=False,
        dest="value_only",
        help="Just print the values of the selected configuration items.",
    )
    config_parser.add_argument(
        "settings", nargs="*", help="Zero or more configuration items to display in the format section.key."
    )
    config_parser.set_defaults(func=config_query)

    configure_requirements_parser = subparsers.add_parser(
        "configure", aliases=["c"], help="Configure Hunter requirements."
    )
    configure_requirements_parser.add_argument(
        "setting", action="store", help="The setting to configure like `section.key`."
    )
    configure_requirements_parser.add_argument(
        "-v", "--value", action="store", default=None, help="The value to set the configuration item to (clear text)."
    )
    configure_requirements_parser.add_argument(
        "-p", "--value-prompt", action="store_true", help="Prompt for this value and hide it from the console."
    )
    configure_requirements_parser.set_defaults(func=configure)

    return True


def execute(args: argparse.Namespace):
    """Execute arguments."""

    if args.debug:
        coloredlogs.install(level="DEBUG", logger=LOGGER)

    args.func(args)

    return


def main(args=None):
    """The main CLI entry point."""

    # configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)s] %(message)s")
    coloredlogs.install(level="INFO", logger=LOGGER)

    if not args:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(description="A hunting tool for ACE ecosystems.")
    build_parser(parser)
    args = parser.parse_args(args)

    return execute(args)
