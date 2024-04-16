#!/bin/bash

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#######################################
# Sources the relevant environment variables.
# Globals:
#   SCRIPT_DIR
# Arguments:
#   None
# Outputs:
#   None
# Returns:
#   1 when sourcing fails, otherwise 0 on success.
#######################################
function load_env_variables() {
  source "${SCRIPT_DIR}/../../scripts/paths.sh" || return 1
  source "${SCRIPT_DIR}/../../scripts/globals.sh" || return 1
}

#######################################
# Check if the Internet is reachable.
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   None
# Returns:
#   0 if the internet is reachable, 1 otherwise.
#######################################
function check_internet() {
    if wget -q --spider "https://google.com"; then
        echo "Internet connection is up."
        return 0
    else
        echo "Internet connection is down."
        return 1
    fi
}

#######################################
# Dynamically manage specified systemd services based on internet connectivity status.
# Globals:
#   None
# Arguments:
#   1. An array of service names to manage
# Outputs:
#   Outputs service management status.
# Returns:
#   None
#######################################
function manage_services() {
    local services=("$@")  # Accept multiple arguments as an array of service names

    local internet_status
    check_internet
    internet_status=$?

    for service_name in "${services[@]}"; do
        if (( internet_status == 0 )); then
            echo "Internet is up - ensuring service ${service_name} is running."
            systemctl is-active --quiet "${service_name}" || systemctl start "${service_name}"
        else
            echo "Internet is down - stopping service ${service_name}."
            systemctl is-active --quiet "${service_name}" && systemctl stop "${service_name}"
            "${PROJECT_PATH}/venv/bin/python3" "${PROJECT_PATH}/src/screen/no_wifi.py" 
        fi
    done
}

#######################################
# Main execution loop.
# Globals:
#   CHECK_INTERVAL
# Arguments:
#   None
# Outputs:
#   Logs status of environment variable loading and service management.
# Returns:
#   None
#######################################
function main() {
    while true; do
        load_env_variables || { echo "Failed to load environment variables."; exit 1; }

        # Define an array of service filenames
        local services=("nfc_reader" "touch_sensor" "screen")

        # Pass the array to manage_services
        manage_services "${services[@]}"
        
        sleep "${CHECK_INTERVAL}"  # Sleep for a configurable number of seconds
    done
}

main
