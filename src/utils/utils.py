from enum import Enum


TIMESTAMP_FORMAT = '%Y-%m-%d %X'


class TapStatus(Enum):
    """Represents the status of a tap."""
    GOOD = 0
    BAD = 1

    def __repr__(self):
        return f'{self.value}'


def get_machine_id() -> str:
    """Retrieves the unique ID of the machine running this program.

    This function specifically targets Unix-like systems. To ensure
    compatibility with non-Unix systems, it returns an empty string.

    Returns:
        str: The device ID if the file exists, otherwise an empty string.
    """
    try:
        with open('/etc/machine-id', 'r') as file:
            return file.read().strip()
    except FileNotFoundError:
        return ''