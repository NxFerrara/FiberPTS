import os
import time

from dotenv import load_dotenv
import supabase
from postgrest import APIResponse

from utils.touch_sensor_utils import Tap
from utils.utils import TIMESTAMP_FORMAT


load_dotenv()


class CloudDBClient:
    """Client for interacting with a cloud database using the Supabase API."""

    def __init__(self):
        """Initializes the client with database credentials.

        Attributes:
            client: Supabase Client instance.
        """
        url = os.getenv('DATABASE_URL')
        key = os.getenv('DATABASE_API_KEY')
        self.client = supabase.create_client(url, key)
    
    def insert_tap_data(self, tap: Tap) -> APIResponse:
        """Inserts a record with timestamp and machine ID into the `tap_data` table.

        Args:
            tap: An instance of Tap containing the data to be inserted

        Returns:
            An APIResponse object representing the result of the database operation.
        """
        # TODO: Implement handling for connection issues.
        # TODO: Implement handling for authentication issues.
        # TODO: Implement data validation.
        # TODO: Implement handling for non-existent table.

        tap_record = {
            'timestamp': time.strftime(TIMESTAMP_FORMAT, time.localtime(tap.timestamp)),
            'machine_id': tap.machine_id
        }
        response = self.client.table('tap_data').insert(tap_record).execute()
        return response
