"""Module defining a CLI Script for some common development tasks"""

import argparse
import json
import logging
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from io import TextIOWrapper
from pathlib import Path
from typing import Optional


def run_command(args: list[str], stdin: Optional[TextIOWrapper] = None, stdout: Optional[TextIOWrapper] = None):
    """
    Runs a command using subprocess
    """
    logging.debug("Running command: %s", " ".join(args))
    # Output using print to ensure order is correct for grouping on github actions (subprocess.run happens before print
    # for some reason)
    popen = subprocess.Popen(
        args, stdin=stdin, stdout=stdout if stdout is not None else subprocess.PIPE, universal_newlines=True
    )
    if stdout is None:
        for stdout_line in iter(popen.stdout.readline, ""):
            print(stdout_line, end="")
        popen.stdout.close()
    return_code = popen.wait()
    return return_code


def start_group(text: str, args: argparse.Namespace):
    """Print the start of a group for Github CI (to get collapsable sections)"""
    if args.ci:
        print(f"::group::{text}")
    else:
        logging.info(text)


def end_group(args: argparse.Namespace):
    """End of a group for Github CI"""
    if args.ci:
        print("::endgroup::")


def run_mongodb_command(args: list[str], stdin: Optional[TextIOWrapper] = None, stdout: Optional[TextIOWrapper] = None):
    """
    Runs a command within the mongodb container
    """
    return run_command(
        [
            "docker",
            "exec",
            "-i",
            "mongodb_container",
        ]
        + args,
        stdin=stdin,
        stdout=stdout,
    )


def run_mongoimport_json_array_file(args: argparse.Namespace, database: str, collection: str, path: Path):
    """
    Runs mongoimport on a MongoDB database to import a json array from a file into a specified collection
    """
    with open(path, "r", encoding="utf-8") as file:
        run_mongodb_command(
            [
                "mongoimport",
            ]
            + get_mongodb_auth_args(args)
            + [
                "--db",
                database,
                "--collection",
                collection,
                "--type=json",
                "--jsonArray",
                "--drop",
            ],
            stdin=file,
        )


def add_mongodb_auth_args(parser: argparse.ArgumentParser):
    """Adds common arguments for MongoDB authentication"""
    parser.add_argument("-u", "--username", default="root", help="Username for MongoDB authentication")
    parser.add_argument("-p", "--password", default="example", help="Password for MongoDB authentication")


def get_mongodb_auth_args(args: argparse.Namespace):
    """Returns arguments in a list to use the parser arguments defined in add_mongodb_auth_args above"""
    return [
        "--username",
        args.username,
        "--password",
        args.password,
        "--authenticationDatabase=admin",
    ]


class SubCommand(ABC):
    """Base class for a sub command"""

    def __init__(self, help: str):
        self.help = help

    @abstractmethod
    def setup(self, parser: argparse.ArgumentParser):
        """Setup the parser by adding any parameters here"""

    @abstractmethod
    def run(self, args: argparse.Namespace):
        """Run the command with the given parameters as added by 'setup'"""


class CommandDBInit(SubCommand):
    """Command that initialises the database

    - Generates a replica set keyfile and sets it's permissions (if it doesn't already exist)
    - Starts the mongodb service (and waits 10 seconds after it starts)
    - Initialises the replica set with a single host
    - Outputs the replica set status
    """

    def __init__(self):
        super().__init__(help="Initialise database for development (using docker on linux)")

    def setup(self, parser: argparse.ArgumentParser):
        add_mongodb_auth_args(parser)

        parser.add_argument(
            "-rsmh",
            "--replicaSetMemberHost",
            default="localhost",
            help="Host to use for the replica set (default: 'localhost')",
        )

    def run(self, args: argparse.Namespace):
        # Generate the keyfile (if it doesn't already exist - this part is linux specific)
        rs_keyfile = Path("./mongodb/keys/rs_keyfile")
        if not rs_keyfile.is_file():
            logging.info("Generating replica set keyfile...")
            with open(rs_keyfile, "w", encoding="utf-8") as file:
                run_command(["openssl", "rand", "-base64", "756"], stdout=file)
            logging.info("Assigning replica set keyfile ownership...")
            run_command(["sudo", "chmod", "0400", "./mongodb/keys/rs_keyfile"])
            run_command(["sudo", "chown", "999:999", "./mongodb/keys/rs_keyfile"])

        start_group("Starting mongodb service", args)
        run_command(["docker", "compose", "up", "-d", "--wait", "--wait-timeout", "30", "mongo-db"])

        # Wait as cannot initialise immediately
        time.sleep(10)
        end_group(args)

        start_group("Initialising replica set", args)
        replicaSetConfig = json.dumps(
            {"_id": "rs0", "members": [{"_id": 0, "host": f"{args.replicaSetMemberHost}:27017"}]}
        )
        run_mongodb_command(
            [
                "mongosh",
            ]
            + get_mongodb_auth_args(args)
            + [
                "--eval",
                f"rs.initiate({replicaSetConfig})",
            ]
        )
        end_group(args)

        # Check the status
        start_group("Checking replica set status", args)
        run_mongodb_command(
            [
                "mongosh",
            ]
            + get_mongodb_auth_args(args)
            + [
                "--eval",
                "rs.status()",
            ],
        )
        end_group(args)


class CommandDBImport(SubCommand):
    """Command that imports data into the database

    By default just the standard data e.g. the units, but with an option to import the generated mock data instead
    """

    def __init__(self):
        super().__init__(help="Imports database for development")

    def setup(self, parser: argparse.ArgumentParser):
        add_mongodb_auth_args(parser)

        parser.add_argument(
            "-g",
            "--generated",
            action="store_true",
            help="Specify this flag to import all generated test data instead of just standard data e.g. units",
        )

    def run(self, args: argparse.Namespace):
        if args.generated:
            # Populate database with generated test data
            with open(Path("./data/mock_data.dump"), "r", encoding="utf-8") as file:
                run_mongodb_command(
                    [
                        "mongorestore",
                    ]
                    + get_mongodb_auth_args(args)
                    + ["--db", "ims", "--archive", "--drop"],
                    stdin=file,
                )
        else:
            # Populate the database with standard data
            start_group("Importing units", args)
            run_mongoimport_json_array_file(args, database="ims", collection="units", path=Path("./data/units.json"))
            end_group(args)


class CommandDBGenerate(SubCommand):
    """Command to generate new test data for the database (runs generate_mock_data.py)

    - Deletes all existing data (after confirmation)
    - Imports units
    - Runs generate_mock_data.py

    Has option to dump the data into './data/mock_data.dump'.
    """

    def __init__(self):
        super().__init__(help="Generates new test data for the database and dumps it")

    def setup(self, parser: argparse.ArgumentParser):
        add_mongodb_auth_args(parser)

        parser.add_argument(
            "-d", "--dump", action="store_false", help="Whether to dump the output into a file that can be committed"
        )

    def run(self, args: argparse.Namespace):
        if args.ci:
            sys.exit("Cannot use --ci with db-generate (currently has interactive input)")

        # Firstly confirm ok with deleting
        answer = input("This operation will replace all existing data, are you sure? ")
        if answer == "y" or answer == "yes":
            # Delete the existing data
            logging.info("Deleting database contents...")
            run_mongodb_command(
                [
                    "mongosh",
                ]
                + get_mongodb_auth_args(args)
                + [
                    "--eval",
                    "db.dropDatabase()",
                ]
            )
            # Import standard data again
            logging.info("Importing standard data...")
            args.generated = False
            commands["db-import"].run(args)
            # Generate new data
            logging.info("Generating new mock data...")
            try:
                # Import here only because CI wont install necessary packages to import it directly
                from generate_mock_data import generate_mock_data

                generate_mock_data()
            except ImportError:
                logging.error("Failed to find generate_mock_data.py")
            if args.dump:
                logging.info("Dumping output...")
                # Dump output again
                with open(Path("./data/mock_data.dump"), "w", encoding="utf-8") as file:
                    run_mongodb_command(
                        [
                            "mongodump",
                        ]
                        + get_mongodb_auth_args(args)
                        + [
                            "--db",
                            "ims",
                            "--archive",
                        ],
                        stdout=file,
                    )


# List of subcommands
commands: dict[str, SubCommand] = {
    "db-init": CommandDBInit(),
    "db-import": CommandDBImport(),
    "db-generate": CommandDBGenerate(),
}


def main():
    """Runs CLI commands"""
    parser = argparse.ArgumentParser(prog="IMS Dev Script", description="Some commands for development")
    parser.add_argument(
        "--debug", action="store_true", help="Flag for setting the log level to debug to output more info"
    )
    parser.add_argument(
        "--ci", action="store_true", help="Flag for when running on Github CI (will output groups for collapsing)"
    )

    subparser = parser.add_subparsers(dest="command")

    for command_name, command in commands.items():
        command_parser = subparser.add_parser(command_name, help=command.help)
        command.setup(command_parser)

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    commands[args.command].run(args)


if __name__ == "__main__":
    main()
