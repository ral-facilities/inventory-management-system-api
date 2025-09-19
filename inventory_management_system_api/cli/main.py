"""Module for providing an admin CLI for managing IMS."""

import typer

from inventory_management_system_api.cli import configure, migrate

app = typer.Typer()
app.add_typer(configure.app, name="configure", help="Configure IMS.")
app.add_typer(migrate.app, name="migrate", help="Manage database migrations in IMS.")


def main():
    """Entrypoint for the ims CLI."""
    app()
