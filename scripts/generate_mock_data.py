import logging
from datetime import timezone
from enum import StrEnum
from typing import Any, Optional

import requests
from faker import Faker

fake = Faker("en_GB")

API_URL = "http://localhost:8000"

MAX_LEVELS_DEEP = 3
MAX_NUMBER_PER_PARENT = 10
PROBABILITY_CATEGORY_IS_LEAF = 0.3  # All MAX_LEVEL_DEEP categories are populated, this just allows them to end earlier
PROBABILITY_CATALOGUE_CATEGORY_HAS_EXTRA_FIELDS = 0.5
MAX_EXTRA_CATALOGUE_CATEGORY_FIELDS = 2
PROBABILITY_CATALOGUE_ITEM_HAS_OPTIONAL_FIELD = 0.5
PROBABILITY_ADDRESS_HAS_OPTIONAL_FIELD = 0.5
PROBABILITY_ITEM_HAS_OPTIONAL_FIELD = 0.5
NUMBER_OF_MANUFACTURERS = 20
PROBABILITY_CATALOGUE_ITEM_HAS_ITEMS = 0.5
MAX_NUMBER_OF_ITEMS_PER_CATALOGUE_ITEM = 5
SEED = 0

logging.basicConfig(level=logging.INFO)

usage_statuses = ["New", "Used", "In Use", "Scrapped"]

manufacturer_names = [
    "Tech Innovators Inc.",
    "Global Gadgets Co.",
    "Precision Electronics Ltd.",
    "Innovate Solutions Group",
    "FutureTech Industries",
    "Smart Devices Innovations",
    "Pinnacle Manufacturing",
    "Infinite Innovations Corp.",
    "Quantum Electronics Ltd.",
    "Advanced Tech Solutions",
    "Innovative Designs Co.",
    "Eco-Tech Manufacturing",
    "Digital Dynamics Inc.",
    "Mega Machines Ltd.",
    "Dynamic Devices Innovations",
    "Ultimate Electronics Corp.",
    "Infinite Innovations Ltd.",
    "Precision Tech Solutions",
    "Global Innovators Group",
    "Dynamic Designs Inc.",
]

catalogue_category_names = [
    "Laser Diodes",
    "Beam Splitters",
    "Fiber OpticCables",
    "Collimating Lens'",
    "Pulse Modulators",
    "Optical Isolators",
    "Laser Crystals",
    "Diffraction Gratings",
    "QSwitchs",
    "Beam Expanders",
    "Output Couplers",
    "Laser Amplifiers",
    "Laser Cavities",
    "Laser Prisms",
    "Photodetectors",
    "Laser Mirrors",
    "Laser Controllers",
    "Laser Spectrometers",
    "Laser Interferometers",
    "Fiber Couplers",
]


class PropertyType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"


available_catalogue_item_properties = [
    {
        "name": "Mirror diameter",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "mm",
        "allowed_values": None,
    },
    {
        "name": "Focal length",
        "type": PropertyType.NUMBER,
        "mandatory": False,
        "unit": "mm",
        "allowed_values": None,
    },
    {
        "name": "Angle",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "degrees",
        "allowed_values": None,
    },
    {
        "name": "Wavelength",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "nm",
        "allowed_values": {"type": "list", "values": [100, 500, 1000, 2000]},
    },
    {
        "name": "Bandwidth",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "nm",
        "allowed_values": None,
    },
    {
        "name": "Pulse length",
        "type": PropertyType.NUMBER,
        "mandatory": False,
        "unit": "ns",
        "allowed_values": None,
    },
    {
        "name": "Frequency",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "Hz",
        "allowed_values": None,
    },
    {
        "name": "Absorption",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "ppm",
        "allowed_values": None,
    },
    {
        "name": "Laser Incident Damage Threshold (LIDT)",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "J/cm²",
        "allowed_values": None,
    },
    {
        "name": "Flatness",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "nm",
        "allowed_values": None,
    },
    {
        "name": "Energy",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "J",
        "allowed_values": None,
    },
    {
        "name": "Output optical power",
        "type": PropertyType.NUMBER,
        "mandatory": True,
        "unit": "W",
        "allowed_values": None,
    },
    {
        "name": "Reflectance",
        "type": PropertyType.STRING,
        "mandatory": True,
        "unit": None,
        "allowed_values": {
            "type": "list",
            "values": [
                "< 0.5% (400 - 700 nm, Average)",
                "< 0.3% (450 nm, 700 nm, per Surface, Average)",
                "< 1% (per Surface, Average)",
            ],
        },
    },
    {
        "name": "Extra details",
        "type": PropertyType.STRING,
        "mandatory": False,
        "unit": None,
        "allowed_values": None,
    },
    {
        "name": "Recently used",
        "type": PropertyType.BOOLEAN,
        "mandatory": False,
        "unit": None,
        "allowed_values": None,
    },
]

system_names = [
    "Laser Star",
    "Photon Wave",
    "Laser Fusion",
    "Laser Strike",
    "Opti Laser",
    "Laser Jet",
    "Pulse Laser",
    "Beam Blaster",
    "Laser Link",
    "Spectralaser",
    "Fiber Pulse",
    "Laser Xpress",
    "Plasma Beam",
    "Quantum Laser",
    "Laser Pulse",
    "Laser Focus",
    "Pico Laser",
    "Mega Beam",
    "Laser Tech",
    "Laser Wave",
]

Faker.seed(0)

# Dictionary with key=id and value=list of dictionaries of the properties
generated_catalogue_categories: dict[str, list[dict]] = {}

# So that replacement item ids can be chosen
# Key is the id and value is the catalogue category it is from
generated_catalogue_items: dict[str, list[str]] = {}

# So that systems can be assigned in items
generated_system_ids: list[str] = []

# Dictionary with key=id and value=list of dictionaries of the usage_status
generated_usage_statuses: dict[str, list[dict]] = {}


def optional_address_field(function):
    return function() if fake.random.random() < PROBABILITY_ADDRESS_HAS_OPTIONAL_FIELD else None


def optional_catalogue_item_field(function):
    return function() if fake.random.random() < PROBABILITY_CATALOGUE_ITEM_HAS_OPTIONAL_FIELD else None


def optional_item_field(function):
    return function() if fake.random.random() < PROBABILITY_ITEM_HAS_OPTIONAL_FIELD else None


def generate_random_catalogue_category(parent_id: str, is_leaf: bool):
    catalogue_item_properties = (
        fake.random.sample(
            available_catalogue_item_properties,
            fake.random.randint(1, MAX_EXTRA_CATALOGUE_CATEGORY_FIELDS),
        )
        if is_leaf and fake.random.random() < PROBABILITY_CATALOGUE_CATEGORY_HAS_EXTRA_FIELDS
        else None
    )

    category: dict = {
        "name": f"{fake.random.choice(catalogue_category_names)}",
        "is_leaf": is_leaf,
        "parent_id": parent_id,
        "catalogue_item_properties": catalogue_item_properties,
    }

    return category


def generate_random_manufacturer():
    return {
        "name": fake.random.choice(manufacturer_names),
        "url": fake.url(),
        "address": {
            "address_line": f"{fake.secondary_address()}, {fake.street_name()}",
            "town": optional_address_field(fake.city),
            "county": optional_address_field(fake.county),
            "country": fake.country(),
            "postcode": fake.postcode(),
        },
        "telephone": fake.phone_number(),
    }


def generate_usage_status(value: str):
    return {
        "value": value,
    }


def generate_random_catalogue_item_property(catalogue_category_property: dict):
    prop = {"id": catalogue_category_property["id"]}

    allowed_values = catalogue_category_property["allowed_values"]
    if allowed_values is not None:
        if allowed_values["type"] == "list":
            return {**prop, "value": fake.random.choice(allowed_values["values"])}
    if catalogue_category_property["type"] == PropertyType.STRING:
        return {**prop, "value": fake.sentence()}
    elif catalogue_category_property["type"] == PropertyType.NUMBER:
        return {**prop, "value": fake.random.random() * 10}
    elif catalogue_category_property["type"] == PropertyType.BOOLEAN:
        return {**prop, "value": fake.random.random() < 0.5}


def generate_random_catalogue_item(
    catalogue_category_id: str,
    manufacturer_id: str,
    catalogue_item_properties: Optional[list[dict]],
):
    obsolete_replacement_catalogue_item_id = optional_catalogue_item_field(
        lambda: (
            fake.random.choice(list(generated_catalogue_items.keys())) if len(generated_catalogue_items) > 0 else None
        )
    )

    properties = None
    if catalogue_item_properties is not None:
        properties = []
        for prop in catalogue_item_properties:
            if prop["mandatory"] or fake.random.random() < PROBABILITY_CATALOGUE_ITEM_HAS_OPTIONAL_FIELD:
                properties.append(generate_random_catalogue_item_property(catalogue_category_property=prop))

    return {
        "catalogue_category_id": catalogue_category_id,
        "manufacturer_id": manufacturer_id,
        "name": fake.random.choice(catalogue_category_names),
        "description": optional_catalogue_item_field(lambda: fake.paragraph(nb_sentences=2)),
        "cost_gbp": fake.random.randint(0, 1000),
        "cost_to_rework_gbp": optional_catalogue_item_field(lambda: fake.random.randint(0, 1000)),
        "days_to_replace": fake.random.randint(0, 100),
        "days_to_rework": optional_catalogue_item_field(lambda: fake.random.randint(0, 100)),
        "drawing_number": optional_catalogue_item_field(lambda: str(fake.random.randint(1000, 10000))),
        "drawing_link": optional_catalogue_item_field(fake.image_url),
        "item_model_number": optional_catalogue_item_field(fake.isbn13),
        "is_obsolete": bool(obsolete_replacement_catalogue_item_id),
        "obsolete_replacement_catalogue_item_id": obsolete_replacement_catalogue_item_id,
        "obsolete_reason": (fake.sentence() if obsolete_replacement_catalogue_item_id is not None else None),
        "manufacturer": {
            "name": fake.name(),
            "address": fake.address(),
            "url": fake.url(),
        },
        "notes": optional_catalogue_item_field(lambda: fake.paragraph(nb_sentences=2)),
        "properties": properties,
    }


def generate_random_item(catalogue_item_id: str):
    properties = None
    category_properties = generated_catalogue_categories[generated_catalogue_items[catalogue_item_id]][
        "catalogue_item_properties"
    ]
    if category_properties is not None:
        properties = [
            generate_random_catalogue_item_property(catalogue_category_property)
            for catalogue_category_property in category_properties
        ]

    return {
        "catalogue_item_id": catalogue_item_id,
        "system_id": fake.random.choice(generated_system_ids),
        "purchase_order_number": fake.isbn10(),
        "is_defective": fake.random.randint(0, 100) > 90,
        "usage_status_id": fake.random.choice(list(generated_usage_statuses.keys())),
        "warranty_end_date": optional_item_field(lambda: fake.date_time(tzinfo=timezone.utc).isoformat()),
        "asset_number": optional_item_field(fake.isbn10),
        "serial_number": optional_item_field(fake.isbn10),
        "delivered_date": optional_item_field(lambda: fake.date_time(tzinfo=timezone.utc).isoformat()),
        "notes": optional_item_field(lambda: fake.paragraph(nb_sentences=2)),
        "properties": properties,
    }


def generate_random_system(parent_id):
    return {
        "name": fake.random.choice(system_names),
        "location": fake.address(),
        "owner": fake.name(),
        "importance": fake.random.choice(["low", "medium", "high"]),
        "description": fake.paragraph(nb_sentences=2),
        "parent_id": parent_id,
    }


def post_avoiding_duplicates(endpoint: str, field: str, json: dict) -> dict[str, Any]:
    """Posts an entity's data to the given endpoint, but adds - n to the end to avoid
    duplicates when a 409 is returned

    Returns:
        str - The ID of the entity created
    """
    index = 0
    status_code = 409
    while status_code == 409:
        response = requests.post(
            f"{API_URL}{endpoint}",
            json=json if index == 0 else {**json, field: f"{json[field]} - {index}"},
            timeout=10,
        )
        status_code = response.status_code
        index += 1
    return response.json()


def create_manufacturer(manufacturer_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/manufacturers", field="name", json=manufacturer_data)


def create_usage_status(usage_status_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/usage-statuses", field="value", json=usage_status_data)


def create_catalogue_category(category_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/catalogue-categories", field="name", json=category_data)


def create_catalogue_item(item_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/catalogue-items", field="name", json=item_data)


def create_system(system_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/systems", field="name", json=system_data)


def create_item(item_data: dict) -> dict[str, Any]:
    return post_avoiding_duplicates(endpoint="/v1/items", field="name", json=item_data)


def populate_random_manufacturers() -> list[str]:
    # Usually faster than append
    manufacturer_ids = [None] * NUMBER_OF_MANUFACTURERS
    for i in range(0, NUMBER_OF_MANUFACTURERS):
        manufacturer_ids[i] = create_manufacturer(generate_random_manufacturer())["id"]
    return manufacturer_ids


def populate_usage_statuses() -> list[str]:
    # Usually faster than append

    for i, usage_status in enumerate(usage_statuses):
        usage_status = generate_usage_status(usage_status)
        usage_status = create_usage_status(usage_status)
        generated_usage_statuses[usage_status["id"]] = usage_status


def populate_random_catalogue_categories(
    available_manufacturers: list[str],
    levels_deep: int = 0,
    parent_id=None,
    is_leaf: bool = False,
    parent_catalogue_category: Optional[dict] = None,
):
    if levels_deep > MAX_LEVELS_DEEP:
        return
    else:
        logging.debug("Populating category with depth %s and is_leaf %s", levels_deep, is_leaf)
        num_to_generate = MAX_NUMBER_PER_PARENT if levels_deep == 0 else fake.random.randint(0, MAX_NUMBER_PER_PARENT)

        for i in range(0, num_to_generate):
            if is_leaf:
                item = generate_random_catalogue_item(
                    catalogue_category_id=parent_id,
                    manufacturer_id=fake.random.choice(available_manufacturers),
                    catalogue_item_properties=(
                        parent_catalogue_category["catalogue_item_properties"] if parent_catalogue_category else None
                    ),
                )
                item_id = create_catalogue_item(item)["id"]
                generated_catalogue_items[item_id] = parent_id
            else:
                # Always make the last level a leaf
                if levels_deep == MAX_LEVELS_DEEP - 1:
                    new_is_leaf = True
                else:
                    new_is_leaf = fake.random.random() < PROBABILITY_CATEGORY_IS_LEAF
                catalogue_category = generate_random_catalogue_category(parent_id, new_is_leaf)
                catalogue_category = create_catalogue_category(catalogue_category)
                generated_catalogue_categories[catalogue_category["id"]] = catalogue_category
                populate_random_catalogue_categories(
                    available_manufacturers=available_manufacturers,
                    levels_deep=levels_deep + 1,
                    parent_id=catalogue_category["id"],
                    is_leaf=new_is_leaf,
                    parent_catalogue_category=catalogue_category,
                )


def populate_random_items():
    for catalogue_item_id in list(generated_catalogue_items.keys()):
        if fake.random.random() < PROBABILITY_CATALOGUE_ITEM_HAS_ITEMS:
            number_to_generate = fake.random.randint(1, MAX_NUMBER_OF_ITEMS_PER_CATALOGUE_ITEM)
            for i in range(0, number_to_generate):
                item = generate_random_item(catalogue_item_id=catalogue_item_id)
                create_item(item)


def populate_random_systems(levels_deep: int = 0, parent_id=None):
    if levels_deep > MAX_LEVELS_DEEP:
        return
    else:
        logging.debug("Populating system with depth %s", levels_deep)
        num_to_generate = MAX_NUMBER_PER_PARENT if levels_deep == 0 else fake.random.randint(0, MAX_NUMBER_PER_PARENT)
        for i in range(0, num_to_generate):
            system = generate_random_system(parent_id)
            system_id = create_system(system)["id"]
            populate_random_systems(levels_deep=levels_deep + 1, parent_id=system_id)
            generated_system_ids.append(system_id)


def generate_mock_data():
    logging.info("Populating usage statuses...")
    populate_usage_statuses()
    logging.info("Populating manufacturers...")
    manufacturer_ids = populate_random_manufacturers()
    logging.info("Populating catalogue categories...")
    populate_random_catalogue_categories(available_manufacturers=manufacturer_ids)
    logging.info("Populating systems...")
    populate_random_systems()
    logging.info("Populating items...")
    populate_random_items()


if __name__ == "__main__":
    generate_mock_data()
