#!/bin/bash

# =============================
# iPhone Photo Backup Script (Menu + Args)
# =============================

DESTINATION="${HOME}/Pictures/iPhoneBackup"   # Default backup folder
VERBOSE=0                                      # 1 = verbose, 0 = silent
MODE="all"                                     # Default mode

install_tools() {
    echo "Checking for required tools..."
    if ! command -v idevicephoto >/dev/null 2>&1; then
        echo "idevicephoto not found, installing..."
        if [[ "$(uname)" == "Linux" ]]; then
            sudo apt update
            sudo apt install -y libimobiledevice6 libimobiledevice-utils ifuse
        elif [[ "$(uname)" == "Darwin" ]]; then
            brew install libimobiledevice
        else
            echo "Unsupported OS. Please install libimobiledevice manually."
            exit 1
        fi
    fi
}

run_backup() {
    mkdir -p "$DESTINATION"

    CMD="idevicephoto download --destination \"$DESTINATION\""
    case "$MODE" in
        all) CMD+=" --all" ;;
        new) CMD+=" --new" ;;
        photos-only) CMD+=" --photos-only" ;;
        videos-only) CMD+=" --videos-only" ;;
        *) echo "Invalid mode: $MODE"; exit 1 ;;
    esac

    if [[ $VERBOSE -eq 1 ]]; then
        CMD+=" --verbose"
        echo "Running command: $CMD"
    fi

    eval $CMD
    echo "Backup completed to $DESTINATION"
}

show_help() {
    echo "iPhone Photo Backup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d DEST    Set destination folder"
    echo "  -m MODE    Download mode: all | new | photos-only | videos-only"
    echo "  -v         Verbose output"
    echo "  -h         Show this help / menu"
    echo ""
    echo "Example:"
    echo "  $0 -d ~/iPhonePhotos -m new -v"
}

parse_args() {
    while getopts "d:m:vh" opt; do
        case $opt in
            d) DESTINATION="$OPTARG" ;;
            m) MODE="$OPTARG" ;;
            v) VERBOSE=1 ;;
            h) show_help; exit 0 ;;
            *) show_help; exit 1 ;;
        esac
    done
}

show_menu() {
    while true; do
        echo ""
        echo "iPhone Backup Menu"
        echo "================="
        echo "1) Backup all photos & videos"
        echo "2) Backup only new photos & videos"
        echo "3) Backup photos only"
        echo "4) Backup videos only"
        echo "5) Change destination folder (current: $DESTINATION)"
        echo "6) Toggle verbose output (current: $VERBOSE)"
        echo "7) Quit"
        echo -n "Choose an option: "
        read -r choice

        case $choice in
            1) MODE="all"; run_backup ;;
            2) MODE="new"; run_backup ;;
            3) MODE="photos-only"; run_backup ;;
            4) MODE="videos-only"; run_backup ;;
            5)
                echo -n "Enter new destination folder: "
                read -r DESTINATION
                echo "Destination folder set to $DESTINATION"
                ;;
            6)
                if [[ $VERBOSE -eq 0 ]]; then VERBOSE=1; else VERBOSE=0; fi
                echo "Verbose mode is now $VERBOSE"
                ;;
            7) echo "Exiting."; exit 0 ;;
            *) echo "Invalid option." ;;
        esac
    done
}

# -------- MAIN --------
install_tools

# If there are CLI arguments, use them; else show menu
if [[ $# -gt 0 ]]; then
    parse_args "$@"
    run_backup
else
    show_menu
fi
