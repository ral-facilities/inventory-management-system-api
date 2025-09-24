"""Module defining a CLI Script for some common development tasks."""

import subprocess
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer()
console = Console()

DatabaseUsernameOption = Annotated[
    str, typer.Option("--db-username", "-dbu", help="Username for MongoDB authentication.", default_factory="root")
]
DatabasePasswordOption = Annotated[
    str,
    typer.Option("--db-password", "-dbp", help="Password for MongoDB authentication.", default_factory="example"),
]
YesOption = Annotated[
    bool,
    typer.Option(
        "--yes",
        "-y",
        help="Confirm without any prompts.",
        # See https://github.com/fastapi/typer/discussions/921 - unfortunately even this doesn't work right now
        # for setting a default. So have to define manually in each function its used.
        # default_factory=lambda: False,
        # show_default="False",
    ),
]


def exit_with_error(message: str):
    """Displays an error message in red and then exits."""

    console.print(f"[red bold]{message}[/]")
    raise typer.Exit(1)


def run_command(args: list[str], stdin: Optional[TextIOWrapper] = None, stdout: Optional[TextIOWrapper] = None):
    """Runs a command using subprocess"""

    console.print(f"[cyan]Running command:[/] [green]{" ".join(args)}[/]")
    # Output using print to ensure order is correct for grouping on github actions (subprocess.run happens before print
    # for some reason)
    with subprocess.Popen(
        args, stdin=stdin, stdout=stdout if stdout is not None else subprocess.PIPE, universal_newlines=True
    ) as popen:
        if stdout is None:
            for stdout_line in iter(popen.stdout.readline, ""):
                console.print(stdout_line, end="")
            popen.stdout.close()
        return_code = popen.wait()

    if return_code != 0:
        exit_with_error("[red]An error occurred while running the last command![/]")


def run_mongodb_command(args: list[str], stdin: Optional[TextIOWrapper] = None, stdout: Optional[TextIOWrapper] = None):
    """Runs a command within the mongodb container"""

    run_command(
        [
            "docker",
            "exec",
            "-i",
            "ims-api-mongodb",
        ]
        + args,
        stdin=stdin,
        stdout=stdout,
    )


def get_mongodb_auth_args(db_username: str, db_password: str):
    """Returns MongoDB authentication arguments in a list."""

    return [
        "--username",
        db_username,
        "--password",
        db_password,
        "--authenticationDatabase=admin",
    ]


@app.command()
def db_import(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption):
    """Imports mock data into the database."""

    # Populate database with generated test data
    with open(Path("./data/mock_data.dump"), "r", encoding="utf-8") as file:
        run_mongodb_command(
            [
                "mongorestore",
            ]
            + get_mongodb_auth_args(db_username, db_password)
            + ["--db", "ims", "--archive", "--drop"],
            stdin=file,
        )
    console.print("Success! :party_popper:")


@app.command()
def db_generate(
    db_username: DatabaseUsernameOption,
    db_password: DatabasePasswordOption,
    dump: Annotated[
        bool, typer.Option("--dump", "-d", help="Whether to dump the output into a file that can be committed.")
    ] = False,
    yes: YesOption = False,
):
    """Generates new test data for the database (runs generate_mock_data.py) and dumps the data if requested."""

    # Firstly confirm ok with deleting
    if not yes:
        confirm = typer.confirm("This operation will replace all existing data, are you sure?")
        if not confirm:
            raise typer.Abort()

    # Delete the existing data
    console.print("Deleting database contents...")
    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
    run_mongodb_command(
        ["mongosh", "ims"]
        + mongodb_auth_args
        + [
            "--eval",
            "db.dropDatabase()",
        ]
    )
    # Ensure setup script is called so any required initial data is populated
    run_mongodb_command(
        ["mongosh", "ims"]
        + mongodb_auth_args
        + [
            "--file",
            "/usr/local/bin/setup.mongodb",
        ]
    )
    # Generate new data
    console.print("Generating new mock data...")
    try:
        # Import here only because CI wont install necessary packages to import it directly
        # pylint:disable=import-outside-toplevel
        from generate_mock_data import generate_mock_data

        generate_mock_data()
    except ImportError:
        exit_with_error("Failed to find generate_mock_data.py")

    console.print("Ensuring previous migration is set to latest...")
    run_command(["ims", "migrate", "set", "latest", "-y"])

    if dump:
        console.print("Dumping output...")
        # Dump output again
        with open(Path("./data/mock_data.dump"), "w", encoding="utf-8") as file:
            run_mongodb_command(
                [
                    "mongodump",
                ]
                + mongodb_auth_args
                + [
                    "--db",
                    "ims",
                    "--archive",
                ],
                stdout=file,
            )
    console.print("Success! :party_popper:")


@app.command()
def db_clear(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption, yes: YesOption = False):
    """Clear all data in MongoDB and repopulate only with what is necessary."""

    # Firstly confirm ok with deleting
    if not yes:
        confirm = typer.confirm("This operation will remove all existing data, are you sure?")
        if not confirm:
            raise typer.Abort()

    # Delete the existing data
    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
    for database_name in ["ims", "test-ims"]:
        console.print("Deleting database contents of %s...", database_name)
        run_mongodb_command(
            ["mongosh", database_name]
            + mongodb_auth_args
            + [
                "--eval",
                "db.dropDatabase()",
            ]
        )
    # Ensure setup script is called so any required initial data is populated again
    run_mongodb_command(
        ["mongosh"]
        + mongodb_auth_args
        + [
            "--file",
            "/usr/local/bin/setup.mongodb",
        ]
    )
    console.print("Success! :party_popper:")


def main():
    """Entrypoint for the IMS Dev CLI."""
    app()


if __name__ == "__main__":
    main()
