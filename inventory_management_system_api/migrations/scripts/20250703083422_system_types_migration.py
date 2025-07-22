"""
Module providing a migration that adds system_types collection and type_id field to systems.
"""

# Expect some duplicate code inside migrations as models can be duplicated
# pylint: disable=invalid-name
# pylint: disable=duplicate-code

from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pymongo.client_session import ClientSession
from pymongo.database import Collection, Database

from inventory_management_system_api.migrations.base import BaseMigration
from inventory_management_system_api.models.custom_object_id_data_types import CustomObjectIdField, StringObjectIdField
from inventory_management_system_api.models.mixins import CreatedModifiedTimeInMixin, CreatedModifiedTimeOutMixin

# Pre-defined system types to create and apply
SYSTEM_TYPE_VALUES = ["Storage", "Operational", "Scrapped"]


class NewSystemBase(BaseModel):
    """
    Base database model for a system.
    """

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    type_id: CustomObjectIdField = None
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class NewSystemIn(CreatedModifiedTimeInMixin, NewSystemBase):
    """
    Input database model for a system.
    """


class OldSystemBase(BaseModel):
    """
    Base database model for a system
    """

    parent_id: Optional[CustomObjectIdField] = None
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    owner: Optional[str] = None
    importance: str

    # Used for uniqueness checks (sanitised name)
    code: str


class OldSystemOut(CreatedModifiedTimeOutMixin, OldSystemBase):
    """
    Output database model for a system
    """

    id: StringObjectIdField = Field(alias="_id")
    parent_id: Optional[StringObjectIdField] = None

    model_config = ConfigDict(populate_by_name=True)


class Migration(BaseMigration):
    """Migration that adds system_types collection and type_id field to systems"""

    description = "Adds system_types collection and type_id field to systems"

    def __init__(self, database: Database):
        self._systems_collection: Collection = database.systems
        self._system_types_collection: Collection = database.system_types

    def forward(self, session: ClientSession):
        """Applies database changes."""

        # Create and obtain the system types
        system_type_ids = self._system_types_collection.insert_many(
            [{"value": value} for value in SYSTEM_TYPE_VALUES], session=session
        ).inserted_ids
        assert len(system_type_ids) == len(SYSTEM_TYPE_VALUES)
        system_types = self._system_types_collection.find(session=session)
        system_type_map = {system_type["value"]: system_type for system_type in system_types}

        # Obtain the root systems and attempt to match their types for them and their subsystems
        root_systems = self._systems_collection.find({"parent_id": None}, session=session)

        for root_system in root_systems:
            system_type_id = system_type_map.get(root_system["name"], system_type_map["Operational"])["_id"]

            self._systems_collection.replace_one(
                {"_id": root_system["_id"]}, self._get_update_data(root_system, system_type_id), session=session
            )
            self._set_system_type_of_child_systems(root_system["_id"], system_type_id, session)

    def _set_system_type_of_child_systems(self, parent_id: ObjectId, parent_type_id: ObjectId, session: ClientSession):
        """Recursively sets the type_id of the children of a parent system.

        Due to pythons max recursion limit of 1000 this migration will only work for < 1000 nested systems.
        """

        subsystems = self._systems_collection.find({"parent_id": parent_id}, session=session)
        for subsystem in subsystems:
            self._systems_collection.replace_one(
                {"_id": subsystem["_id"]}, self._get_update_data(subsystem, parent_type_id), session=session
            )
            if subsystem["parent_id"] is not None:
                self._set_system_type_of_child_systems(subsystem["_id"], parent_type_id, session)

    def _get_update_data(self, system: dict, type_id: ObjectId):
        """Obtains the update data for a system when a type id is inserted into it (keeps the same order as the
        models)."""
        old_system = OldSystemOut(**system)
        new_system = NewSystemIn(**old_system.model_dump(), type_id=str(type_id))
        return {**new_system.model_dump(), "modified_time": system["modified_time"]}

    def backward(self, session: ClientSession):
        """Reverses database changes."""

        self._systems_collection.update_many({}, {"$unset": {"type_id": ""}}, session=session)

    def backward_after_transaction(self):
        """Called after the backward function is called to do anything that can't be done inside a transaction."""

        self._system_types_collection.drop()
