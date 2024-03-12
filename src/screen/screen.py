import time
import os
import logging
import logging.config

from PIL import Image, ImageDraw, ImageFont

from config.screen_config import *
from src.utils.paths import (TOUCH_SENSOR_TO_SCREEN_PIPE,
                             DEVICE_STATE_PATH,
                             PROJECT_DIR)
from src.utils.screen_utils import (DisplayAttributes,
                                    DashboardAttributes,
                                    PopupAttributes,
                                    read_device_state,
                                    write_device_state,
                                    get_image_center,
                                    read_pipe,
                                    write_image_to_fb)
from src.utils.utils import TapStatus


SAVED_TIMESTAMP_FORMAT = '%Y-%m-%d'

logging.config.fileConfig(f"{PROJECT_DIR}/config/logging.conf")
logger = logging.getLogger(os.path.basename(__file__))

class Screen:
    """This class handles drawing text, images, and popups to a screen. It includes functionality for rotating the display for correct orientation, managing the screen's framebuffer for rendering, reading touch sensor data through a named pipe, and updating the display based on the incoming data.

    Attributes:
        display_attributes (DisplayAttributes): Attributes related to display properties like framebuffer path, height, width, and frame rate.
        dashboard_attributes (DashboardAttributes): Attributes related to dashboard appearance such as font family, size, color, and background color.
        popup_attributes (PopupAttributes): Attributes for configuring popups, including fonts, colors, and duration.
        touch_sensor_pipe (str): Path to the named pipe for reading touch sensor data.
        device_state_path (str): Path to the file where the device state is stored.
        device_state (dict): State of the device as read from the device state file.
        image: Current image being displayed on the screen.
    """

    def __init__(self) -> None:
        """Initialize the Screen instance with the specified display properties, font settings, and file paths."""
        # Configurations
        self.display_attributes = DisplayAttributes()
        self.dashboard_attributes = DashboardAttributes()
        self.popup_attributes = PopupAttributes()
        # File paths
        self.touch_sensor_pipe = TOUCH_SENSOR_TO_SCREEN_PIPE
        self.device_state_path = DEVICE_STATE_PATH
        # Initialize screen
        self.device_state = read_device_state(DEVICE_STATE_PATH)
        self.image = None
        self.create_image(self.dashboard_attributes.dashboard_bg_color)

    def create_image(self, bg_color: str) -> None:
        """Create an image with the specified background color (assumes the screen needs 90 degree rotation).

        Args:
            bg_color (str): Background color for the image.
        """
        self.image = Image.new('RGB', (self.display_attributes.display_height, self.display_attributes.display_width),
                               bg_color)

    def draw_image(self) -> None:
        """Draw the current image to the display (assumes the screen needs 90 degree rotation)."""
        if self.image:
            self.image = self.image.rotate(90, expand=True)
            write_image_to_fb(self.image, self.display_attributes.display_fb_path,
                              self.display_attributes.display_fb_lock_path)

    def add_text(self,
                 text: str,
                 position: tuple[int, int],
                 font_family: str,
                 font_size: int,
                 font_color: str,
                 centered: bool = False) -> None:
        """Add text to the current image at the specified position.

        Args:
            text (str): The text to be added.
            position (tuple[int, int]): The position (x, y) where the text will be added.
            font_family (str): The font family to be used for the text.
            font_size (int): The font size of the text.
            font_color (str): The color of the text.
            centered (bool): If True, centers the text at the given position.
        """
        if self.image:
            draw = ImageDraw.Draw(self.image)
            font = ImageFont.truetype(font_family, font_size)
            if centered:
                ascent, descent = font.getmetrics()
                bbox = font.getbbox(text)
                text_width, text_height = bbox[2] - bbox[0], ascent + descent
                position = (position[0] - text_width // 2, position[1] - text_height // 2)
            draw.text(position, text, font=font, fill=font_color)

    def draw_dashboard(self) -> None:
        """Draw the dashboard interface on the screen."""
        self.create_image(self.dashboard_attributes.dashboard_bg_color)
        image_center = get_image_center(self.image)
        date_str = time.strftime(SAVED_TIMESTAMP_FORMAT, time.localtime(time.time()))
        self.add_text(date_str, (0, 0),
                      self.dashboard_attributes.dashboard_font_family,
                      self.dashboard_attributes.dashboard_font_size,
                      self.dashboard_attributes.dashboard_font_color,
                      centered=False)
        self.add_text(f"Unit Count: {self.device_state['unit_count']}",
                      image_center,
                      self.dashboard_attributes.dashboard_font_family,
                      self.dashboard_attributes.dashboard_font_size,
                      self.dashboard_attributes.dashboard_font_color,
                      centered=True)
        self.draw_image()

    def draw_popup(self, text: str, bg_color: str) -> None:
        """Draw a popup message on the screen with specified text and background color.

        Args:
            text (str): The message text to display in the popup.
            bg_color (str): The background color for the popup.
        """
        self.create_image(bg_color)
        image_center = get_image_center(self.image)
        self.add_text(text,
                      image_center,
                      self.popup_attributes.message_attributes.popup_font_family,
                      self.popup_attributes.message_attributes.popup_font_size,
                      self.popup_attributes.message_attributes.popup_font_color,
                      centered=True)
        self.draw_image()
        time.sleep(self.popup_attributes.popup_duration)

    def handle_pipe_data(self) -> None:
        """Handle data received from the touch sensor pipe. Updates device state and draws popups based on the received data."""
        tap_data = read_pipe(self.touch_sensor_pipe)
        if tap_data:
            logger.info('Tap received by screen')
            # TODO: We may decide to store this data from a stopwatch time.
            # timestamp = tap_data["timestamp"]
            status = TapStatus[tap_data['status']]
            if status == TapStatus.GOOD:
                self.device_state['unit_count'] += 1
                write_device_state(self.device_state, self.device_state_path)
                self.draw_popup(self.popup_attributes.message_attributes.tap_event_message,
                                self.popup_attributes.event_attributes.tap_event_bg_color)
            elif status == TapStatus.BAD:
                self.draw_popup(self.popup_attributes.message_attributes.popup_warning_message,
                                self.popup_attributes.event_attributes.popup_warning_bg_color)
            return True
        return False

    def run(self) -> None:
        """Start the main loop of the screen, updating the display at the set frame rate and handling incoming pipe data."""
        logger.info('Running main loop')
        frame_duration = 1.0 / self.display_attributes.display_frame_rate
        self.draw_dashboard()
        while True:
            time.sleep(frame_duration)
            if self.handle_pipe_data():
                self.draw_dashboard()


if __name__ == "__main__":
    logger.info('Starting screen.py')
    screen = Screen()
    screen.run()
