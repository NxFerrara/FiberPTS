# APPLICATION PATH CONFIGURATION
PROJECT_DIR=/opt
PROJECT_PATH=${PROJECT_DIR}/FiberPTS
DEVICE_STATE_FILE_PATH=${PROJECT_PATH}/app/device_state.json

# SYSTEM PATH CONFIGURATION
SYSTEMD_DIR=/etc/systemd/system
DISPLAY_FRAME_BUFFER_LOCK_PATH=${PROJECT_PATH}/app/locks/frame_buffer.lock
DISPLAY_FRAME_BUFFER_PATH=/dev/fb2
DISPLAY_ERROR_COUNT_THRESHOLD=4

# NAMED PIPES CONFIGURATION
PIPE_FOLDER_PATH=${PROJECT_PATH}/app/pipes
TOUCH_SENSOR_TO_SCREEN_PIPE=${PIPE_FOLDER_PATH}/touch_sensor_to_screen_pipe
NFC_TO_SCREEN_PIPE=${PIPE_FOLDER_PATH}/nfc_to_screen_pipe

# FLAG FILE PATHS
PRE_REBOOT_FLAG_FILE=${PROJECT_PATH}/app/flags/pre_reboot_setup.flag
POST_REBOOT_FLAG_FILE=${PROJECT_PATH}/app/flags/post_reboot_setup.flag
OVERLAY_MERGED_FLAG_FILE=${PROJECT_PATH}/app/flags/overlay_merged.flag