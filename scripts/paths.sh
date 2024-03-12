# Application Paths
PROJECT_DIR=/opt
PROJECT_PATH=${PROJECT_DIR}/FiberPTS
DEVICE_STATE_PATH=${PROJECT_PATH}/.app/data/device_state.json

# System Path Configuration
SYSTEMD_DIR=/etc/systemd/system
DISPLAY_FRAME_BUFFER_LOCK_PATH=${PROJECT_PATH}/.app/locks/frame_buffer.lock
DISPLAY_FRAME_BUFFER_PATH=/dev/fb2

# Named Pipe Paths
PIPE_FOLDER_PATH=${PROJECT_PATH}/.app/pipes
TOUCH_SENSOR_TO_SCREEN_PIPE=${PIPE_FOLDER_PATH}/touch_sensor_to_screen_pipe
NFC_TO_SCREEN_PIPE=${PIPE_FOLDER_PATH}/nfc_to_screen_pipe

# Flag File Paths
PRE_REBOOT_FLAG=${PROJECT_PATH}/.app/flags/pre_reboot_setup_done.flag
POST_REBOOT_FLAG=${PROJECT_PATH}/.app/flags/post_reboot_setup_done.flag
REBOOT_HALTED_FLAG=${PROJECT_PATH}/.app/flags/reboot_halted.flag
OVERLAY_MERGED_FLAG=${PROJECT_PATH}/.app/flags/overlay_merged.flag

# Log-related Paths
LOGROTATE_PATH=/etc/logrotate.d
LOG_FILENAME=fpts.log
LOGCONF_FILENAME=fpts_log.conf
