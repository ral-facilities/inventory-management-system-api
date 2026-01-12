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
    """Runs a command using subprocess."""

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
    """Runs a command within the mongodb container."""

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


def clear_existing_data(
    db_username: DatabaseUsernameOption,
    db_password: DatabasePasswordOption,
    yes: YesOption,
):
    """Clears any existing data in the database. Requires confirmation if yes is false."""

    # Firstly confirm if ok with deleting
    if not yes:
        confirm = typer.confirm("This operation will remove all existing data, are you sure?")
        if not confirm:
            raise typer.Abort()

    # Delete the existing data
    console.print("Deleting database contents...")
    run_mongodb_command(
        ["mongosh", "ims"]
        + get_mongodb_auth_args(db_username, db_password)
        + [
            "--eval",
            "db.dropDatabase()",
        ]
    )

def dump_database(
    db_username: DatabaseUsernameOption,
    db_password: DatabasePasswordOption,
    file_name: str
):
    """Dumps the data within the database to a database dump file."""

    console.print("Dumping database contents...")

    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
    with open(Path(f"./data/{file_name}.dump"), "w", encoding="utf-8") as file:
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

def restore_database(
    db_username: DatabaseUsernameOption,
    db_password: DatabasePasswordOption,
    file_name: str
):
    """Restores the data within the database from database dump file."""

    console.print("Restoring database contents...")

    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
    with open(Path(f"./data/{file_name}.dump"), "r", encoding="utf-8") as file:
        run_mongodb_command(
            [
                "mongorestore",
            ]
            + mongodb_auth_args
            + ["--db", "ims", "--archive", "--drop"],
            stdin=file,
        )

@app.command()
def db_dump(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption, file_name: Annotated[
        str, typer.Argument(help="File name of the file to dump the database contents to.")
    ] = False,):
    """Dumps data in the database to a database dump file."""

    dump_database(db_username, db_password, file_name)
    console.print("Success! :party_popper:")

@app.command()
def db_restore(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption, file_name: Annotated[
        str, typer.Argument(help="File name of the restore the database contents from.")
    ] = False,):
    """Restores data in the database from a database dump file."""

    restore_database(db_username, db_password, file_name)
    console.print("Success! :party_popper:")

@app.command()
def db_import(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption):
    """Imports mock data into the database."""

    # Populate database with generated test data
    restore_database(db_username, db_password, "mock_data")
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

    # First clear the existing data
    clear_existing_data(db_username, db_password, yes)

    # Ensure setup script is called so any required initial data is populated
    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
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
        # Dump output again
        dump_database(db_username, db_password, "mock_data")
    console.print("Success! :party_popper:")


@app.command()
def db_clear(db_username: DatabaseUsernameOption, db_password: DatabasePasswordOption, yes: YesOption = False):
    """Clear all data in MongoDB and repopulate only with what is necessary."""

    # First clear the existing data
    clear_existing_data(db_username, db_password, yes)

    # Ensure setup script is called so any required initial data is populated again
    mongodb_auth_args = get_mongodb_auth_args(db_username, db_password)
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