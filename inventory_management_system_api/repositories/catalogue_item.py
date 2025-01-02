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
from inventory_management_system_api.core.exceptions import ChildElementsExistError, MissingRecordError
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

    def create(self, catalogue_item: CatalogueItemIn, session: ClientSession = None) -> CatalogueItemOut:
        """
        Create a new catalogue item in a MongoDB database.

        :param catalogue_item: The catalogue item to be created.
        :param session: PyMongo ClientSession to use for database operations
        :return: The created catalogue item.
        """
        logger.info("Inserting the new catalogue item into the database")
        result = self._catalogue_items_collection.insert_one(catalogue_item.model_dump(by_alias=True), session=session)
        catalogue_item = self.get(str(result.inserted_id), session=session)
        return catalogue_item

    def get(self, catalogue_item_id: str, session: ClientSession = None) -> Optional[CatalogueItemOut]:
        """
        Retrieve a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to retrieve.
        :param session: PyMongo ClientSession to use for database operations
        :return: The retrieved catalogue item, or `None` if not found.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        logger.info("Retrieving catalogue item with ID: %s from the database", catalogue_item_id)
        catalogue_item = self._catalogue_items_collection.find_one({"_id": catalogue_item_id}, session=session)
        if catalogue_item:
            return CatalogueItemOut(**catalogue_item)
        return None

    def list(self, catalogue_category_id: Optional[str], session: ClientSession = None) -> List[CatalogueItemOut]:
        """
        Retrieve all catalogue items from a MongoDB database.

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :param session: PyMongo ClientSession to use for database operations
        :return: A list of catalogue items, or an empty list if no catalogue items are returned by the database.
        """
        query = {}
        if catalogue_category_id:
            catalogue_category_id = CustomObjectId(catalogue_category_id)
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
        self, catalogue_item_id: str, catalogue_item: CatalogueItemIn, session: ClientSession = None
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
        catalogue_item = self.get(str(catalogue_item_id), session=session)
        return catalogue_item

    def delete(self, catalogue_item_id: str, session: ClientSession = None) -> None:
        """
        Delete a catalogue item by its ID from a MongoDB database.

        :param catalogue_item_id: The ID of the catalogue item to delete.
        :param session: PyMongo ClientSession to use for database operations
        :raises MissingRecordError: If the catalogue item doesn't exist.
        """
        catalogue_item_id = CustomObjectId(catalogue_item_id)
        if self.has_child_elements(catalogue_item_id, session=session):
            raise ChildElementsExistError(
                f"Catalogue item with ID {str(catalogue_item_id)} has child elements and cannot be deleted"
            )

        logger.info("Deleting catalogue item with ID: %s from the database", catalogue_item_id)
        result = self._catalogue_items_collection.delete_one({"_id": catalogue_item_id}, session=session)
        if result.deleted_count == 0:
            raise MissingRecordError(f"No catalogue item found with ID: {str(catalogue_item_id)}")

    def has_child_elements(self, catalogue_item_id: CustomObjectId, session: ClientSession = None) -> bool:
        """
        Check if a catalogue item has child elements based on its ID.

        Child elements in this case means whether a catalogue item has child items

        :param catalogue_item_id: The ID of the catalogue item to check
        :param session: PyMongo ClientSession to use for database operations
        :return: True if the catalogue item has child elements, False otherwise.
        """
        logger.info("Checking if catalogue item with ID '%s' has child elements", catalogue_item_id)
        item = self._items_collection.find_one({"catalogue_item_id": catalogue_item_id}, session=session)
        return item is not None

    def list_ids(self, catalogue_category_id: Optional[str] = None, session: ClientSession = None) -> List[ObjectId]:
        """
        Retrieve a list of all catalogue item ids with a specific catalogue_category_id from a MongoDB
        database. Performs a projection to only include _id. (Required for mass updates of properties
        to reduce memory usage)

        :param catalogue_category_id: The ID of the catalogue category to filter catalogue items by.
        :param session: PyMongo ClientSession to use for database operations
        :return: A list object catalogue item ObjectId's or an empty list if no catalogue items are returned by
                 the database.
        """

        query = {}
        if catalogue_category_id:
            catalogue_category_id = CustomObjectId(catalogue_category_id)
            query["catalogue_category_id"] = catalogue_category_id

        message = "Retrieving IDs of all catalogue items from the database"
        if not query:
            logger.info(message)
        else:
            logger.info("%s matching the provided catalogue category ID filter", message)
            logger.debug("Provided catalogue category ID filter: %s", catalogue_category_id)

        # Using distinct has a 16MB limit
        # https://stackoverflow.com/questions/29771192/how-do-i-get-a-list-of-just-the-objectids-using-pymongo
        # For 100000 documents, using list comprehension takes about 0.85 seconds vs 0.50 seconds for distinct
        return self._catalogue_items_collection.find(query, {"_id": 1}, session=session).distinct("_id")

    def insert_property_to_all_matching(
        self, catalogue_category_id: str, property_in: PropertyIn, session: ClientSession = None
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
        self, property_id: str, new_property_name: str, session: ClientSession = None
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

    def update_number_of_spares(
        self,
        catalogue_item_id: Optional[ObjectId],
        number_of_spares: Optional[int],
        session: Optional[ClientSession] = None,
    ) -> None:
        """
        Updates the `number_of_spares` field using a given catalogue item id filter.

        :param catalogue_item_id: The ID of the catalogue item to update or `None` if updating all.
        :param number_of_spares: New number of spares to update to. A value of `None` can be used to write lock
                                 the involved documents when updating within a transaction as the actual value will be
                                 assigned later but the documents should be write locked immediately.
        :param session: PyMongo ClientSession to use for database operations.
        """

        if catalogue_item_id is not None:
            self._catalogue_items_collection.update_one(
                {"_id": catalogue_item_id},
                {"$set": {"number_of_spares": number_of_spares}},
                session=session,
            )
        else:
            self._catalogue_items_collection.update_many(
                {},
                {"$set": {"number_of_spares": number_of_spares}},
                session=session,
            )
