import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv('.env.shared')

# File paths to named pipes
TOUCH_SENSOR_TO_SCREEN_PIPE = os.getenv('TOUCH_SENSOR_TO_SCREEN_PIPE')
NFC_TO_SCREEN_PIPE = os.getenv('NFC_TO_SCREEN_PIPE')