import os
import configparser
import logging

from typing import Dict

from ace_hunter.config import CONFIG

LOGGER = logging.getLogger("ace_hunter.hunt_type")


def validate_hunt_type_config_requirements(requirements: Dict, config: configparser.ConfigParser = CONFIG):
    """Validate that all required config items are present."""
    passed = True
    for requirement in requirements:
        if requirement not in config.sections():
            LOGGER.warning(f"required {requirement} section is missing from config.")
            LOGGER.warning(
                f"the following {requirement} section config items are required: {requirements[requirement]}."
            )
            return False
        for item in requirements[requirement]:
            if item not in config[requirement]:
                LOGGER.warning(f"required {requirement}.{item} is missing from config.")
                passed = False
            elif not config[requirement][item]:
                LOGGER.warning(f"required {requirement}.{item} is empty in config.")
                passed = False
    return passed
