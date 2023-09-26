#!/usr/bin/python3.9
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import time
import requests
import json
import datetime
from zoneinfo import ZoneInfo
import sys
import os
import signal
import boto3
from boto3.dynamodb.conditions import Key, Attr
import configparser
import netifaces as ni


BATCH_FILE_PATH = "/var/lib/screen/batched_button_presses.json"
LAST_TAGS_AND_IDS_FILE_PATH = "/var/lib/screen/last_tags_and_ids.json"
AIRTABLE_API_KEY = ""


def handle_sigterm(signum, frame):
    """
    Handles the SIGTERM signal to gracefully exit the program.

    Parameters:
    - signum: The signal number.
    - frame: The current stack frame.

    Returns:
    - None
    """
    print_log("Received SIGTERM, ending program...")
    sys.exit(0)  # Exit the program


def print_log(format_str, *args):
    """
    Logs messages with a timestamp.

    Parameters:
    - format_str: The format string for the message.
    - *args: Arguments to format the string.

    Returns:
    - None
    """
    current_time = datetime.datetime.now(ZoneInfo('US/Eastern'))
    timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')

    if format_str.startswith('\n'):
        print(f"\n{timestamp}::screen.py::", end='')  # add newline before the timestamp
        format_str = format_str[1:]  # remove the first character
    else:
        print(f"{timestamp}::screen.py::", end='')

    print(format_str.format(*args))


def perror_log(format_str, *args):
    """
    Logs error messages with a timestamp.

    Parameters:
    - format_str: The format string for the error message.
    - *args: Arguments to format the string.

    Returns:
    - None
    """
    current_time = datetime.datetime.now(ZoneInfo('US/Eastern'))
    timestamp = current_time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp}::screen.py::{format_str.format(*args)}", file=sys.stderr)


def get_machine_id():
    """
    Retrieves the machine ID from the system.

    Returns:
    - str: The machine ID or None if not found.
    """
    try:
        with open("/etc/machine-id", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # If /etc/machine-id doesn't exist, you can also check /var/lib/dbus/machine-id
        try:
            with open("/var/lib/dbus/machine-id", "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None
    return None


def get_local_ip(interface='wlan0'):
    """
    Retrieves the local IP address of the specified interface.

    Parameters:
    - interface: The network interface to check. Default is 'wlan0'.

    Returns:
    - str: The IP address or 'UNKNOWN' if not found.
    """
    try:
        ip = ni.ifaddresses(interface)[ni.AF_INET][0]['addr']
    except (KeyError, ValueError):
        ip = 'UNKNOWN'
    return ip


def format_utc_to_est(date_str):
    """
    Converts a UTC datetime string to EST and formats it.

    Parameters:
    - date_str: The UTC datetime string.

    Returns:
    - str: The formatted EST datetime string.
    """
    if not date_str or date_str == "None":
        return ""
    date_str = date_str.replace('Z', '')
    # Adjust the format to match the given string
    date_utc = datetime.datetime.fromisoformat(date_str).astimezone(datetime.timezone.utc)
    date_est = date_utc.astimezone(ZoneInfo('America/New_York'))
    if date_est.astimezone(ZoneInfo('US/Eastern')).dst():
        date_est += datetime.timedelta(hours=1)
    return date_est.strftime('%Y-%m-%d %l:%M %p')


def get_current_time(format_seconds=True):
    """
    Retrieves the current time in EST.

    Parameters:
    - format_seconds: Whether to include seconds in the format.

    Returns:
    - str: The formatted EST datetime string.
    """
    # Get current UTC time
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Convert to Eastern Time Zone
    now_est = now_utc.astimezone(ZoneInfo('America/New_York'))
    # Format the time to desired format: date, time, AM/PM
    if format_seconds:
        return now_est.strftime('%Y-%m-%d %l:%M:%S %p')
    return now_est.strftime('%Y-%m-%d %l:%M %p')


def draw_rotated_text(image, text, font, position, text_color, bg_color):
    """
    Draws rotated text onto an image.

    Parameters:
    - image: The PIL Image object to draw on.
    - text: The text to draw.
    - font: The font to use.
    - position: The (x, y) position to draw the text.
    - text_color: The color of the text.
    - bg_color: The background color.

    Returns:
    - Image: The modified image with the rotated text.
    """
    draw = ImageDraw.Draw(image)
    # Draw text onto a separate image
    text_width, text_height = draw.textsize(text, font=font)
    text_image = Image.new("RGB", (text_width, text_height), bg_color)
    text_draw = ImageDraw.Draw(text_image)
    text_draw.text((0, 0), text, font=font, fill=text_color)

    # Rotate the text image by 90 degrees
    rotated_text = text_image.rotate(90, expand=True)

    # Paste the rotated text onto the main image at the calculated x-position
    image.paste(rotated_text, (position[1], image.height - rotated_text.height - position[0]))
    return image


def image_to_rgb565(image):
    """
    Converts a PIL Image to RGB565 format.

    Parameters:
    - image: The PIL Image object.

    Returns:
    - np.array: The image data in RGB565 format.
    """
    # Split into R, G, B channels
    r, g, b = image.split()

    # Convert each channel to an appropriate numpy array
    r = np.array(r, dtype=np.uint16)
    g = np.array(g, dtype=np.uint16)
    b = np.array(b, dtype=np.uint16)

    # Right shift to fit into 565 format
    r >>= 3  # Keep top 5 bits
    g >>= 2  # Keep top 6 bits
    b >>= 3  # Keep top 5 bits

    # Combine into RGB 565 format
    rgb565 = (r << 11) | (g << 5) | b

    # Convert the 2D array to a 1D array (raw data)
    raw_data = rgb565.ravel()

    return raw_data


def create_image(width, height, bg_color):
    """
    Creates a new PIL Image with the specified dimensions and background color.

    Parameters:
    - width: The width of the image.
    - height: The height of the image.
    - bg_color: The background color.

    Returns:
    - Image: The created PIL Image object.
    """
    return Image.new("RGB", (width, height), bg_color)


def write_to_framebuffer(data, path="/dev/fb1"):
    """
    Writes data to the framebuffer device.

    Parameters:
    - data: The data to write.
    - path: The path to the framebuffer device. Default is "/dev/fb1".

    Returns:
    - None
    """
    with open(path, "wb") as f:
        f.write(data.tobytes())


def draw_display(last_tags_and_ids, res=(240, 320), font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24), bg_color=(255, 0, 0), text_color=(255, 255, 255)):
    """
    Creates and draws an image for display based on the provided data.

    Parameters:
    - last_tags_and_ids: A dictionary containing data to display.
    - res: The resolution of the image. Default is (240, 320).
    - font: The font to use for text. Default is DejaVuSans-Bold with size 24.
    - bg_color: The background color. Default is red.
    - text_color: The text color. Default is white.

    Returns:
    - None
    """
    image = create_image(res[0], res[1], bg_color)

    image = draw_rotated_text(image, last_tags_and_ids["employee_name"], font, (5, 0), text_color, bg_color)
    image = draw_rotated_text(image, last_tags_and_ids["last_employee_tap"], font, (5, 30), text_color, bg_color)

    image = draw_rotated_text(image, last_tags_and_ids["order_id"], font, (5, 60), text_color, bg_color)
    image = draw_rotated_text(image, last_tags_and_ids["last_order_tap"], font, (5, 90), text_color, bg_color)

    image = draw_rotated_text(image, "Total Count: " + str(last_tags_and_ids["units_employee"]), font, (5, 120), text_color, bg_color)

    image = draw_rotated_text(image, "Order Count: " + str(last_tags_and_ids["units_order"]), font, (5, 150), text_color, bg_color)

    # Convert the image to RGB565 format and write to framebuffer
    raw_data = image_to_rgb565(image)
    write_to_framebuffer(raw_data)


def save_last_tags_and_ids_to_file(last_tags_and_ids):
    """
    Saves the last tags and IDs data to a file.

    Parameters:
    - last_tags_and_ids: A dictionary containing the data to save.

    Returns:
    - None
    """
    with open(LAST_TAGS_AND_IDS_FILE_PATH, 'w') as file:
        json.dump(last_tags_and_ids, file)


def load_last_tags_and_ids_from_file():
    """
    Loads the last tags and IDs data from a file.

    Returns:
    - dict: The loaded data or an empty dictionary if not found.
    """
    try:
        with open(LAST_TAGS_AND_IDS_FILE_PATH, 'r') as file:
            try:
                return json.load(file)
            except json.decoder.JSONDecodeError:
                return {}
    except FileNotFoundError:
        return {}

def save_batch_to_file(batch):
    """
    Saves the current batched button presses to a file.

    Parameters:
    - batch: A dictionary containing the batched button presses.

    Returns:
    - None
    """
    with open(BATCH_FILE_PATH, 'w') as file:
        json.dump(batch, file)

def load_batch_from_file():
    """
    Loads the saved batched button presses from a file.

    Returns:
    - dict: The loaded batched button presses or an empty dictionary if not found.
    """
    try:
        with open(BATCH_FILE_PATH, 'r') as file:
            content = file.read()
            if not content.strip():  # Check if file is empty
                return {"Records": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"Records": []}
    except json.JSONDecodeError:  # Handle invalid JSON
        return {"Records": []}


def get_record(base_id, table_id, field_ids, filter_id, filter_value):
    """
    Retrieves a record from Airtable based on the provided criteria.

    Parameters:
    - base_id: The ID of the Airtable base.
    - table_id: The ID of the table within the base.
    - field_ids: A list of field IDs and their corresponding names.
    - filter_id: The field ID to filter on.
    - filter_value: The value to filter on.

    Returns:
    - dict: The retrieved record data.
    """
    global AIRTABLE_API_KEY
    api_key = AIRTABLE_API_KEY
    URL = f"https://api.airtable.com/v0/{base_id}/{table_id}?returnFieldsByFieldId=true"

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-type": "application/json"
    }

    all_records = []
    offset = None

    # Pagination loop
    while True:
        if offset:
            paginated_url = f"{URL}&offset={offset}"
        else:
            paginated_url = URL

        response = requests.get(paginated_url, headers=HEADERS)
        data = json.loads(response.text)

        if response.status_code != 200:
            perror_log(f"Error {response.status_code}: {json.dumps(response.text)}")
            break

        all_records.extend(data.get("records", []))

        # Check if there's an offset for the next set of records
        offset = data.get("offset")
        if not offset:
            break

    # Filter records
    filtered_records = []
    for record in all_records:
        fields = record.get("fields", {})
        if fields.get(filter_id) == filter_value:
            filtered_records.append(fields)

    reader_data = {}
    if filtered_records:
        for field_id, name in field_ids:
            reader_data[name] = filtered_records[0].get(field_id, "None")

    return reader_data


def create_record(base_id, table_id, field_data):
    """
    Creates a new record in Airtable.

    Parameters:
    - base_id: The ID of the Airtable base.
    - table_id: The ID of the table within the base.
    - field_data: A dictionary of field IDs and their values.

    Returns:
    - dict: The created record data.
    """
    global AIRTABLE_API_KEY
    api_key = AIRTABLE_API_KEY
    URL = f"https://api.airtable.com/v0/{base_id}/{table_id}?returnFieldsByFieldId=True"

    HEADERS = {
        "Authorization": f"Bearer {api_key}",
        "Content-type": "application/json"
    }

    payload = {
        "records": [{"fields": field_data}]
    }

    response = requests.post(URL, headers=HEADERS, data=json.dumps(payload))

    if response.status_code != 200:
        perror_log(f"Error {response.status_code}: {json.dumps(response.text)}")
        return None
    return json.loads(response.text)


def push_item_db(dynamodb, request_type, request_data):
    """
    Pushes an item to a DynamoDB table.

    Parameters:
    - dynamodb: The boto3 DynamoDB resource.
    - request_type: The type of request.
    - request_data: The data for the request.

    Returns:
    - tuple: A tuple containing a boolean indicating success and the partition key.
    """
    table = dynamodb.Table('API_Requests')
    partition_key = f'{get_machine_id()}-{request_type}-{get_current_time()}'
    response = table.put_item(
        Item={
            'partitionKey': partition_key,
            'Request_Type': request_type,
            'Data': json.dumps(request_data),
            'Status': 'Pending',
        }
    )
    metaData = response.get('ResponseMetadata', 'None')
    if metaData != 'None':
        status = metaData.get('HTTPStatusCode', 'None')
        if status == 200:
            return True, partition_key
    return False, None


def pull_item_db(dynamodb, partition_key, max_attempts=5):
    """
    Pulls an item from a DynamoDB table based on the partition key.

    Parameters:
    - dynamodb: The boto3 DynamoDB resource.
    - partition_key: The partition key for the item.
    - max_attempts: The maximum number of attempts to retrieve the item.

    Returns:
    - tuple: A tuple containing a boolean indicating success and the item data or an error message.
    """
    table = dynamodb.Table('API_Requests')
    attempts = 1
    while attempts <= max_attempts:
        try:
            # Retrieve the item from the DynamoDB table
            response = table.get_item(
                Key={
                    'partitionKey': partition_key
                }
            )

            # Extract the item from the response
            item = response.get('Item', {})

            # Check if the item exists and has the status "Complete"
            if item and item.get('Status') == 'Complete':
                key = {
                    'partitionKey': partition_key
                }
                table.delete_item(Key=key)
                return True, item
            attempts += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"An error occurred while pulling the item: {e}")
            return False, f"An error occurred: {e}"
    return False, "Item not found or not complete"


def main():
    # Reading Airtable API Key
    airtable_config = configparser.ConfigParser()
    airtable_config.read('/home/potato/.airtable/credentials.txt')
    global AIRTABLE_API_KEY  # Making sure to use the global variable
    AIRTABLE_API_KEY = airtable_config.get('Credentials', 'airtable_api_key')

    # Load AWS credentials from file
    aws_config = configparser.ConfigParser()
    aws_config.read('/home/potato/.aws/credentials.txt')

    aws_access_key_id = aws_config.get('Credentials', 'aws_access_key_id')
    aws_secret_access_key = aws_config.get('Credentials', 'aws_secret_access_key')

    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name='us-east-1'
    )

    signal.signal(signal.SIGTERM, handle_sigterm)
    print_log("Starting Screen.py")
    print_log("Pulling Previous Data")

    # Load the last tags, ids, and taps from file
    last_tags_and_ids = load_last_tags_and_ids_from_file()
    print(last_tags_and_ids)
    machine_id = get_machine_id()
    if last_tags_and_ids.get("machine_record_id","None") == "None":
        request_data = {
            'table_name': 'tblFOfDowcZNlPRDL',
            'filter_id': 'fldbh9aMmA6qAoNKq',
            'filter_value': machine_id,
            'field_mappings': [
                ("fldZsM3YEVQqpJMFF", "record_id"),
                ("fldfXLG8xbM9S3Evx", "order_tag_record_id"),
                ("fldN0cePGQy8jMkBa", "employee_tag_record_id"),
                ("fldcaeaey2E5R8Iqp", "last_order_tap"),
                ("fldVALQ4NGPNVrvZz", "last_employee_tap"),
                ("fldcFVtGOWbd8RgT6", "order_id"),
                ("fldJQd3TmtxURsQy0", "employee_name")
            ]
        }
        success, partition_key = push_item_db(dynamodb, "GetRecord", request_data)
        if success:
            success, db_data = pull_item_db(dynamodb, partition_key)
            if success:
                reader_dict = json.loads(db_data['Data'])['Records'][0]
                last_tags_and_ids["machine_record_id"] = reader_dict.get('record_id', ' ')
                last_tags_and_ids["last_order_record_id"] = reader_dict.get("order_tag_record_id", " ")[0]
                last_tags_and_ids["last_employee_record_id"] = reader_dict.get("employee_tag_record_id", " ")[0]
                last_tags_and_ids["last_order_tap"] = format_utc_to_est(reader_dict.get("last_order_tap", ""))
                last_tags_and_ids["last_employee_tap"] = format_utc_to_est(reader_dict.get("last_employee_tap", ""))
                last_tags_and_ids["order_id"] = reader_dict.get("order_id", " ")[0]
                last_tags_and_ids["employee_name"] = reader_dict.get("employee_name", " ")[0]
                last_tags_and_ids["units_employee"] = last_tags_and_ids["units_order"] = 0
                last_tags_and_ids["last_employee_tag"] = last_tags_and_ids["last_order_tag"] = "None"
    print(last_tags_and_ids)
    # Obtain local IP address of the Linux machine on wlan0
    local_ip = get_local_ip()

    # Push local IP address along with machine_record_id to DynamoDB
    request_data = {
        "local_ip": local_ip,
        "machine_record_id": last_tags_and_ids.get("machine_record_id", "None")
    }

    if push_item_db(dynamodb, "LocalIPAddress", request_data)[0]:
        print_log(f"Local IP Address pushed successfully: {local_ip}")
    else:
        print_log("Failed to push Local IP Address.")

    # Load the batched button presses from file
    button_presses = load_batch_from_file()
    fifo_path = "/tmp/screenPipe"

    fail = False
    batch_count = 10
    current_count = len(button_presses["Records"])  # Update current count based on the loaded batch
    print_log("Starting Display")
    try:
        while True:
            # Create an image and draw rotated text onto it
            draw_display(last_tags_and_ids)
            time.sleep(0.25)
            with open(fifo_path, "r") as fifo:
                data = fifo.read()
                if data:
                    print(data)
                    data = data.split("-program-")
                    formatted_time = get_current_time(format_seconds=False)
                    formatted_time_sec = get_current_time(format_seconds=True)
                    if data[0] == "read_ultralight.c":
                        if data[1][:-1] == "Failed":
                            fail = True
                        else:
                            tagId = data[1][:-1].lower()
                            request_data = {
                                'table_name': 'tbl6vse0gHkuPxBaT',
                                'filter_id': 'fldRHuoXAQr4BF83j',
                                'filter_value': tagId,
                                'field_mappings': [
                                    ("fldRi8wjAdfBkDhH8", "record_id"),
                                    ("fldSrxknmVrsETFPx", "order_id")
                                ]
                            }
                            success, partition_key = push_item_db(dynamodb, "GetRecord", request_data)
                            if success:
                                success, db_data = pull_item_db(dynamodb, partition_key)
                                if success:
                                    order_dict = json.loads(db_data['Data'])['Records'][0]
                                    print(order_dict)
                            field_ids = [("fldSrxknmVrsETFPx","order_id"), ("fldRi8wjAdfBkDhH8","record_id")]
                            order_dict = get_record("appZUSMwDABUaufib", "tbl6vse0gHkuPxBaT", field_ids, "fldRHuoXAQr4BF83j", tagId)
                            # When an employee tag is registered, the session unit counting is reset
                            if order_dict: # Order tag is registered
                                if tagId != last_tags_and_ids["last_order_tag"]:
                                    if last_tags_and_ids["last_employee_record_id"] == "None":
                                        fail = True
                                    else:
                                        last_tags_and_ids["last_order_record_id"] = order_dict["record_id"]
                                        request_data = {
                                            "machine_record_id": [last_tags_and_ids["machine_record_id"]],
                                            "order_tag_record_id": [last_tags_and_ids["last_order_record_id"]],
                                            "employee_tag_record_id": [last_tags_and_ids["last_employee_record_id"]]
                                        }
                                        if push_item_db(dynamodb, "OrderNFC", request_data):
                                            print_log("NFC Order Tapped")
                                            last_tags_and_ids["last_order_tag"] = tagId
                                            last_tags_and_ids["last_order_tap"] = formatted_time
                                            last_tags_and_ids["units_order"] = 0
                                            last_tags_and_ids["order_id"] = "None" if order_dict["order_id"] == "None" else order_dict["order_id"][0]
                                        else:
                                            fail = True
                            else: # Unregistered tag treated as employee tag or employee tag is registered
                                if tagId != last_tags_and_ids["last_employee_tag"]:
                                    last_employee_record_id_temp = last_tags_and_ids["last_employee_record_id"]
                                    employee_name_temp = last_tags_and_ids["employee_name"]
                                    # TODO: NEED TO IMPLEMENT GetRecord API CALL THROUGH EC2
                                    field_ids = [("fldOYvm4LsaM9pJNw", "employee_name"),("fld49C1CkqgW9hA3p","record_id")]
                                    employee_dict = get_record("appZUSMwDABUaufib", "tblbRYLt6rr4nTbP6", field_ids,
                                                               "fldyYKc2g0dBdolKQ", tagId)
                                    if employee_dict:
                                        last_tags_and_ids["employee_name"] = employee_dict["employee_name"][0]
                                        last_tags_and_ids["last_employee_record_id"] = employee_dict["record_id"]
                                    else:
                                        last_tags_and_ids["employee_name"] = tagId
                                        # TODO: NEED TO IMPLEMENT CreateRecord API CALL THROUGH EC2
                                        field_data = {"fldyYKc2g0dBdolKQ": tagId}
                                        tag_record = create_record("appZUSMwDABUaufib", "tblbRYLt6rr4nTbP6",
                                                                   field_data)
                                        last_tags_and_ids["last_employee_record_id"] = tag_record["records"][0]["fields"]["Record ID"]
                                    request_data = {
                                        "machine_record_id": [last_tags_and_ids["machine_record_id"]],
                                        "employee_tag_record_id": [last_tags_and_ids["last_employee_record_id"]]
                                    }
                                    if push_item_db(dynamodb, "EmployeeNFC", request_data):
                                        print_log("NFC Employee Tapped")
                                        last_tags_and_ids["last_employee_tag"] = tagId
                                        last_tags_and_ids["last_employee_tap"] = formatted_time
                                        last_tags_and_ids["units_order"] = 0
                                        last_tags_and_ids["units_employee"] = 0
                                    else:
                                        last_tags_and_ids["last_employee_record_id"] = last_employee_record_id_temp
                                        last_tags_and_ids["employee_name"] = employee_name_temp
                                        fail = True
                    else: # Button tap increases unit count
                        if last_tags_and_ids["last_employee_tag"] != "None" and last_tags_and_ids["last_order_tag"] != "None":
                            print_log("Button Pressed")
                            request_data = {
                                "machine_record_id": last_tags_and_ids["machine_record_id"],
                                "employee_tag_record_id": last_tags_and_ids["last_employee_record_id"],
                                "order_tag_record_id": last_tags_and_ids["last_order_record_id"],
                                "timestamp": formatted_time_sec
                            }
                            button_presses["Records"].append(request_data)
                            current_count += 1
                            if current_count >= batch_count: # May have to partition into multiple batches of 10
                                if push_item_db(dynamodb, "TapEvent", button_presses):
                                    current_count = 0
                                    button_presses = {"Records": []}
                                else:
                                    fail = True
                            last_tags_and_ids["units_order"] += 1
                            last_tags_and_ids["units_employee"] += 1
                        else:
                            fail = True
                        save_batch_to_file(button_presses)
                    save_last_tags_and_ids_to_file(last_tags_and_ids)
                    temp_color = (0,170,0)
                    if fail:
                        temp_color = (0,0,255)
                        fail = False
                    draw_display(last_tags_and_ids, bg_color=temp_color)
            time.sleep(0.25)
    except KeyboardInterrupt:
        print_log("Program Interrupted")

if __name__ == "__main__":
    main()