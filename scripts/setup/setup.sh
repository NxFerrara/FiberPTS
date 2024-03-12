#!/bin/bash
#
# This script facilitates the setup of FiberPTS, including pre-reboot and 
# post-reboot configurations. It load environment variables required during the
# setup, creates necessary directories, and executes scripts for both
# pre-reboot and post-reboot tasks based on the command-line argument passed.

set -e

# Setup color support for status messages if terminal supports colors
if [ -t 1 ] && [ -n "$(tput colors)" ]; then
  RED="$(tput setaf 1)"
  GREEN="$(tput setaf 2)"
  YELLOW="$(tput setaf 3)"
  BLUE="$(tput setaf 4)"
  MAGENTA="$(tput setaf 5)"
  CYAN="$(tput setaf 6)"
  WHITE="$(tput setaf 7)"
  BOLD="$(tput bold)"
  RESET="$(tput sgr0)"
else
  # Fallback to no color if stdout does not support it
  RED=""
  GREEN=""
  YELLOW=""
  BLUE=""
  MAGENTA=""
  CYAN=""
  WHITE=""
  BOLD=""
  RESET=""
fi
export RED GREEN YELLOW BLUE MAGENTA CYAN WHITE BOLD RESET

# Status Messages
OK="${GREEN}[OK]     ${RESET}"
WARNING="${YELLOW}[WARNING]${RESET}"
FAIL="${RED}[FAIL]   ${RESET}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

#######################################
# Ensures the script is run with root privileges, exiting with an error
# if it's not.
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   Error message to stdout and exits with status 1 if not run as root.
#######################################
function assert_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo -e "${WARNING} This script must be run as root. Please use sudo."
    exit 1
  fi
}

#######################################
# Loads environment variables from specified files in the project directory.
# Globals:
#   SCRIPT_DIR
# Arguments:
#   None
# Outputs:
#   None
#######################################
function load_env_variables() {
  local project_path="${SCRIPT_DIR}/../../"
  set -a
  source "${project_path}/scripts/paths.sh"
  source "${project_path}/.env"
  set +a
}

#######################################
# Executes all shell scripts in the given directory.
# Globals:
#   None
# Arguments:
#   target_dir - Directory containing scripts to execute.
# Outputs:
#   Status messages for each script executed.
# TODO: Add script name to output messages for clarity.
#######################################
function run_scripts() {
  local target_dir="$1"
  readonly target_dir
  shift

  set +e
  for script in "${target_dir}"/*.sh; do
    echo "Running $(basename ${script})..."
    if ! bash "${script}" 2>&1; then
      echo "${FAIL} ${script##*/}"
      exit 2
    fi
    echo "${OK} ${script##*/}"
  done
  set -e
}

#######################################
# Manages pre-reboot tasks, including running scripts and handling user prompts
# for rebooting the system.
# Globals:
#   SCRIPT_DIR, PRE_REBOOT_FLAG, REBOOT_HALTED_FLAG
# Arguments:
#   None
# Outputs:
#   Status messages for pre-reboot tasks and prompts the user for reboot.
#######################################
function run_pre_reboot_tasks() {
  if [ ! -f "${PRE_REBOOT_FLAG}" ] && [ ! -f "${REBOOT_HALTED_FLAG}" ]; then
    echo "${BOLD}Initiating pre-reboot setup...${RESET}"
    run_scripts "${SCRIPT_DIR}/pre_reboot"
    echo "${GREEN}${BOLD}Pre-reboot tasks completed.${RESET}"
  elif [ -f "${REBOOT_HALTED_FLAG}" ]; then
    echo "${WARNING} Pre-reboot setup already completed."
  elif [ -f "${PRE_REBOOT_FLAG}" ]; then
    echo "${WARNING} Pre-reboot setup already completed."
    exit 0
  fi

  while true; do
    read -p "Do you wish to reboot now? [Y/n] " response
    case "${response}" in
      [Yy]*)
        touch "${DISPLAY_FRAME_BUFFER_LOCK_PATH}"
        touch "${PRE_REBOOT_FLAG}"
        if [ -f "${REBOOT_HALTED_FLAG}" ]; then
          rm -f "${REBOOT_HALTED_FLAG}"
        fi
        echo "Rebooting..."
        reboot --no-wall
        break
        ;;
      [Nn]*)
        touch "${REBOOT_HALTED_FLAG}"
        echo "${WARNING} Post-reboot setup won't begin until system is rebooted."
        break
        ;;
      *)
        echo "Invalid input. Please answer 'Y' (yes) or 'n' (no)."
        ;;
    esac
  done
  exit 0
}

#######################################
# Manages post-reboot tasks, including verifying prerequisites and executing
# scripts for post-reboot configuration.
# Globals:
#   SCRIPT_DIR, PRE_REBOOT_FLAG, POST_REBOOT_FLAG
# Arguments:
#   None
# Outputs:
#   Status messages for post-reboot tasks and initiates a reboot upon completion.
#######################################
function run_post_reboot_tasks() {
  echo "Checking post-reboot requirements..."
  if [ ! -f "${PRE_REBOOT_FLAG}" ]; then
    echo "${FAIL} Pre-reboot dependencies missing."
    exit 1
  elif [ -f "${POST_REBOOT_FLAG}" ]; then
    echo "${WARNING} Post-reboot setup already completed."
    exit 0
  fi
  echo "${OK} All requirements satisfied."

  echo -e "\n${BOLD}Initiating post-reboot setup...${RESET}"
  run_scripts "${SCRIPT_DIR}/post_reboot"
  touch "${POST_REBOOT_FLAG}"

  echo -e "\n${BOLD}FiberPTS${RESET} setup is done. System will reboot now."
  reboot > /dev/null
}

#######################################
# Creates necessary application directories for flags, locks, logs, and pipe
# folders.
# Globals:
#   PROJECT_PATH, PIPE_FOLDER_PATH
# Arguments:
#   None
# Outputs:
#   None
#######################################
function setup_app_directory() {
  mkdir -p "${PROJECT_PATH}"/.app/data
  touch "${DEVICE_STATE_PATH}"

  mkdir -p "${PROJECT_PATH}"/.app/flags
  mkdir -p "${PROJECT_PATH}"/.app/locks
  mkdir -p "${PROJECT_PATH}"/.app/logs
  mkdir -p "${PIPE_FOLDER_PATH}"
}

#######################################
# Displays usage information for the script.
# Globals:
#   None
# Arguments:
#   None
# Outputs:
#   Usage information to stdout.
#######################################
function print_usage() {
  echo "Usage: $0 --pre | --post"
}

#######################################
# Orchestrates the script's execution flow based on command-line arguments,
# facilitating either pre-reboot or post-reboot setup.
# Globals:
#   None
# Arguments:
#   Command-line arguments specifying setup phase (--pre or --post).
# Outputs:
#   Calls functions to perform setup tasks based on the specified phase.
#######################################
function main() {
  assert_root
  load_env_variables

  make_app_directories
  case "$1" in
    --pre)
      run_pre_reboot_tasks
      ;;
    --post)
      run_post_reboot_tasks
      ;;
    *)
      echo "$0: Invalid option '$1'"
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
