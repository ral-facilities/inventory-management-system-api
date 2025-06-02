"""
Module for setting up and configuring the logging system.
"""

import logging
import logging.config


def setup_logger() -> None:
    """
    Set up the logger using the configuration INI file.
    """
    logging.config.fileConfig("logging.ini")
