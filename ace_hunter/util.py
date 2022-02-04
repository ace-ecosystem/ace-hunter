# various utility functions

import os
import datetime
import logging

from zoneinfo import ZoneInfo

from ace_hunter.config import CONFIG, WORK_DIR

LOGGER = logging.getLogger("ace_hunter.util")


def local_time():
    """Returns the local time in UTC as a timezone aware datetime object."""
    return datetime.datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))


def abs_path(path: str, relative_dir: str = None):
    """Return absolute path depending on environment and path.

    Returns path if path is absolute.
    Returns relative_dir/path if relative_dir is given.
    Returns SAQ_HOME/path if SAQ_HOME in os.enviro.
    Returns ace_hunter.config.WORK_DIR/path otherwise.
    """
    if os.path.isabs(path):
        return path

    if relative_dir is not None:
        return os.path.join(relative_dir, path)

    if "SAQ_HOME" in os.environ:
        return os.path.join(os.environ["SAQ_HOME"], path)

    if not os.path.exists(WORK_DIR):
        LOGGER.warning(f"WORK_DIR {WORK_DIR} has not yet been created.")

    return os.path.join(WORK_DIR, path)


def create_timedelta(timespec):
    """Utility function to translate DD:HH:MM:SS into a timedelta object."""
    duration = timespec.split(":")
    seconds = int(duration[-1])
    minutes = 0
    hours = 0
    days = 0

    if len(duration) > 1:
        minutes = int(duration[-2])
    if len(duration) > 2:
        hours = int(duration[-3])
    if len(duration) > 3:
        days = int(duration[-4])

    return datetime.timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours)


def create_directory(path):
    """Creates the given directory and returns the path."""
    if not os.path.isdir(path):
        os.makedirs(path)
    return path
