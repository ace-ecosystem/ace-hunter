"""Configuration related items.
"""

import os
import stat
import logging
import tzlocal
import zoneinfo

from datetime import datetime
from configparser import ConfigParser

LOGGER = logging.getLogger("ace_hunter.config")

HOME_PATH = os.path.dirname(os.path.abspath(__file__))

default_config_path = os.path.join(HOME_PATH, "etc", "defaults.ini")
user_config_path = os.path.join(os.path.expanduser("~"), ".config", "ace", "hunting.ini")
CONFIG_SEARCH_PATHS = [
    default_config_path,
    "/opt/ace/etc/saq.hunting.ini",
    "/etc/ace/hunting.ini",
    user_config_path,
]

CONFIG = ConfigParser()
CONFIG.read(CONFIG_SEARCH_PATHS)

# NOTE: we're not creating this directory here as it's not used for most use cases.
WORK_DIR = CONFIG.get("ace_hunter", "work_dir", fallback=os.path.join(os.path.expanduser("~"), ".ace", "hunter"))
if "SAQ_HOME" in os.environ:
    # If SAQ_HOME is set, we're running in an ACE environment.
    WORK_DIR = os.environ["SAQ_HOME"]
DATA_DIR = os.path.join(WORK_DIR, CONFIG.get("global", "data_dir", fallback="data"))

# local timezone
LOCAL_TIMEZONE = zoneinfo.ZoneInfo(tzlocal.get_localzone_name())


# ACE default queue. Allow for this to be overrideable via environment variable.
ACE_DEFAULT_QUEUE = "default"
if "ACE_DEFAULT_QUEUE" in os.environ:
    ACE_DEFAULT_QUEUE = os.environ["ACE_DEFAULT_QUEUE"]


ANALYSIS_MODE_CORRELATION = "correlation"
DEFAULT_ANALYSIS_MODE = CONFIG.get("ace_hunter", "default_correlation_mode", fallback=ANALYSIS_MODE_CORRELATION)
if "ACE_DEFAULT_CORRELATION_MODE" in os.environ:
    DEFAULT_ANALYSIS_MODE = os.environ["ACE_DEFAULT_CORRELATION_MODE"]

# the expected format of the event_time of an ACE alert
event_time_format_tz = "%Y-%m-%d %H:%M:%S %z"


def save_configuration(config: ConfigParser, save_path=user_config_path):
    """Write config to save_path."""
    if not os.path.exists(os.path.dirname(save_path)):
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    try:
        with open(save_path, "w") as fp:
            config.write(fp)
        if os.path.exists(save_path):
            # set permissions to RW for owner only.
            os.chmod(save_path, stat.S_IREAD | stat.S_IWRITE)
            LOGGER.info(f"saved configuration to: {save_path}")
        return True
    except FileNotFoundError:
        LOGGER.error(f"part of path does not exist: {save_path}")
        return False


def save_config_item(section: str, item: str, value: str, save_path=user_config_path):
    """Save value to section.item in save_path."""
    LOGGER.info(f"saving passed value to {section}.{item} to {save_path}")
    config = ConfigParser()
    config.read(save_path)
    if not config.has_section(section):
        config.add_section(section)
    config.set(section, item, value)
    return save_configuration(config, save_path)
