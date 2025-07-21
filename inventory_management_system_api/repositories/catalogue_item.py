"""
Module for providing a repository for managing catalogue items in a MongoDB database.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from bson import ObjectId
from pymongo.client_session import ClientSession
from pymongo.collection import Collection

from inventory_management_system_api.core.custom_object_id import CustomObjectId
from inventory_management_system_api.core.database import DatabaseDep
from inventory_management_system_api.core.exceptions import InvalidObjectIdError, MissingRecordError
from inventory_management_system_api.models.catalogue_item import CatalogueItemIn, CatalogueItemOut, PropertyIn

logger = logging.getLogger()


class CatalogueItemRepo:
    """
    Repository for managing catalogue items in a MongoDB database.
    """

    def __init__(self, database: DatabaseDep) -> None:
        """
        Initialize the `CatalogueItemRepo` with a MongoDB database instance.

        :param database: The database to use.
        """
        self._database = database
        self._catalogue_items_collection: Collection = self._database.catalogue_items
        self._items_collection: Collection = self._database.items

    def create(self, catalogue_item: CatalogueItemIn, session: Optional[ClientSession] = None) -> CatalogueItemOut:
        """
        Create a new catalogue item in a MongoDB database.

        :param catalogue_item: The catalogue item to be created.
        :param session: PyMongo ClientSession to use for database operations
        :return: The created catalogue item.
        """
        logger.info("Inserting the new catalogue item into the database")
        result = self._catalogue_items_collection.insert_one(catalogue_item.model_dump(by_alias=True), session=session)
        return self.get(str(result.inserted_id), session=session)

    def get(
        self,
        catalogue_item_id: str,
        session: Optional[ClientSession] = None,
    ) -> CatalogueItemOut:
        """
        Retrieve a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to retrieve.
        :param session: PyMongo ClientSession to use for database operations
        :return: The retrieved catalogue item, or `None` if not found.
        :raises MissingRecordError: If the supplied `catalogue_item_id` is non-existent.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)

        logger.info("Retrieving catalogue item with ID: %s from the database", catalogue_item_id)
        catalogue_item = self._catalogue_items_collection.find_one({"_id": catalogue_item_id}, session=session)

        if catalogue_item:
            return CatalogueItemOut(**catalogue_item)

        raise MissingRecordError(entity_id=catalogue_item_id, entity_type="catalogue item")

    def list(
        self, catalogue_category_id: Optional[str], session: Optional[ClientSession] = None
    ) -> List[CatalogueItemOut]:
        """
        Retrieve all catalogue items from a MongoDB database.

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :param session: PyMongo ClientSession to use for database operations
        :return: A list of catalogue items, or an empty list if no catalogue items are returned by the database.
        """
        query = {}
        if catalogue_category_id:
            try:
                catalogue_category_id = CustomObjectId(catalogue_category_id)
            except InvalidObjectIdError:
                # As this method filters, and to hide the database behaviour, we treat any invalid id
                # the same as a valid one that doesn't exist i.e. return an empty list
                return []
            query["catalogue_category_id"] = catalogue_category_id

        message = "Retrieving all catalogue items from the database"
        if not query:
            logger.info(message)
        else:
            logger.info("%s matching the provided catalogue category ID filter", message)
            logger.debug("Provided catalogue category ID filter: %s", catalogue_category_id)

        catalogue_items = self._catalogue_items_collection.find(query, session=session)
        return [CatalogueItemOut(**catalogue_item) for catalogue_item in catalogue_items]

    def update(
        self, catalogue_item_id: str, catalogue_item: CatalogueItemIn, session: Optional[ClientSession] = None
    ) -> CatalogueItemOut:
        """
        Update a catalogue item by its ID in a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to update.
        :param catalogue_item: The catalogue item containing the update data.
        :param session: PyMongo ClientSession to use for database operations
        :return: The updated catalogue item.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)

        logger.info("Updating catalogue item with ID: %s in the database", catalogue_item_id)
        self._catalogue_items_collection.update_one(
            {"_id": catalogue_item_id}, {"$set": catalogue_item.model_dump(by_alias=True)}, session=session
        )
        return self.get(str(catalogue_item_id), session=session)

    def delete(self, catalogue_item_id: str, session: Optional[ClientSession] = None) -> None:
        """
        Delete a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to delete.
        :param session: PyMongo ClientSession to use for database operations
        :raises MissingRecordError: If the catalogue item doesn't exist.
        """
        logger.info("Deleting catalogue item with ID: %s from the database", catalogue_item_id)
        result = self._catalogue_items_collection.delete_one(
            {"_id": CustomObjectId(catalogue_item_id)},
            session=session,
        )
        if result.deleted_count == 0:
            raise MissingRecordError(entity_id=catalogue_item_id, entity_type="catalogue item")

    def has_child_elements(self, catalogue_item_id: str, session: Optional[ClientSession] = None) -> bool:
        """
        Check if a catalogue item has child elements based on its ID.

        Child elements in this case means whether a catalogue item has child items

        :param catalogue_item_id: The ID of the catalogue item to check.
        :param session: PyMongo ClientSession to use for database operations.
        :return: True if the catalogue item has child elements, False otherwise.
        """
        logger.info("Checking if catalogue item with ID '%s' has child elements", catalogue_item_id)
        item = self._items_collection.find_one(
            {"catalogue_item_id": CustomObjectId(catalogue_item_id)},
            session=session,
        )
        return item is not None

    def is_replacement_for(self, catalogue_item_id: str, session: Optional[ClientSession] = None) -> bool:
        """
        Check if a catalogue item is the replacement for at least one obsolete catalogue item.

        :param catalogue_item_id: The ID of the catalogue item to check.
        :param session: PyMongo ClientSession to use for database operations.
        :return: True if the catalogue item is the replacement for at least one obsolete catalogue item, False
                 otherwise.
        """
        logger.info(
            "Checking if catalogue item with ID '%s' is the replacement for an obsolete catalogue item",
            catalogue_item_id,
        )
        item = self._catalogue_items_collection.find_one(
            {"obsolete_replacement_catalogue_item_id": CustomObjectId(catalogue_item_id)}, session=session
        )
        return item is not None

    def list_ids(self, catalogue_category_id: str, session: Optional[ClientSession] = None) -> List[ObjectId]:
        """
        Retrieve a list of all catalogue item ids with a specific catalogue_category_id from a MongoDB
        database. Performs a projection to only include _id. (Required for mass updates of properties
        to reduce memory usage)

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :param session: PyMongo ClientSession to use for database operations
        :return: A list object catalogue item ObjectId's or an empty list if no catalogue items are returned by
                 the database.
        """
        logger.info(
            "Finding the id's of all catalogue items within the catalogue category with ID '%s' in the database",
            catalogue_category_id,
        )

        # Using distinct has a 16MB limit
        # https://stackoverflow.com/questions/29771192/how-do-i-get-a-list-of-just-the-objectids-using-pymongo
        # For 100000 documents, using list comprehension takes about 0.85 seconds vs 0.50 seconds for distinct
        return self._catalogue_items_collection.find(
            {"catalogue_category_id": CustomObjectId(catalogue_category_id)}, {"_id": 1}, session=session
        ).distinct("_id")

    def insert_property_to_all_matching(
        self, catalogue_category_id: str, property_in: PropertyIn, session: Optional[ClientSession] = None
    ):
        """
        Inserts a property into every catalogue item with a given catalogue_category_id via an update_many query

        :param catalogue_category_id: The ID of the catalogue category who's catalogue items to update
        :param property_in: The property to insert into the catalogue items' properties list
        :param session: PyMongo ClientSession to use for database operations
        """

        logger.info(
            "Inserting property into catalogue item's with a catalogue category ID: %s in the database",
            catalogue_category_id,
        )

        self._catalogue_items_collection.update_many(
            {"catalogue_category_id": CustomObjectId(catalogue_category_id)},
            {
                "$push": {"properties": property_in.model_dump(by_alias=True)},
                "$set": {"modified_time": datetime.now(timezone.utc)},
            },
            session=session,
        )

    def update_names_of_all_properties_with_id(
        self, property_id: str, new_property_name: str, session: Optional[ClientSession] = None
    ) -> None:
        """
        Updates the name of a property in every catalogue item it is present in

        Also updates the modified_time to reflect the update

        :param property_id: The ID of the property to update
        :param new_property_name: The new property name
        :param session: PyMongo ClientSession to use for database operations
        """

        logger.info("Updating all properties with ID: %s inside catalogue items in the database", property_id)

        self._catalogue_items_collection.update_many(
            {"properties._id": CustomObjectId(property_id)},
            {
                "$set": {
                    "properties.$[elem].name": new_property_name,
                    "modified_time": datetime.now(timezone.utc),
                }
            },
            array_filters=[{"elem._id": CustomObjectId(property_id)}],
            session=session,
        )
