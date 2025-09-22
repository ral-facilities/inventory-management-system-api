"""Module for providing an admin CLI for managing IMS."""

import typer

from inventory_management_system_api.cli import configure, create, delete, migrate, update

app = typer.Typer()
app.add_typer(configure.app, name="configure", help="Configure IMS.")
app.add_typer(migrate.app, name="migrate", help="Manage database migrations in IMS.")
app.add_typer(create.app, name="create", help="Create entities in IMS.")
app.add_typer(update.app, name="update", help="Update entities in IMS.")
app.add_typer(delete.app, name="delete", help="Delete entities in IMS.")


def main():
    """Entrypoint for the ims CLI."""
    app()
