#!/bin/bash

# Simple time sync helper
# Usage:
#   scripts/sync_time.sh              # sync host with NTP if possible
#   scripts/sync_time.sh containers   # show guidance for container time sync
#
# Note:
# - Container clocks follow the host kernel clock. If container time is off,
#   fix the host time. Setting time inside containers usually requires extra caps.

set -euo pipefail

command_exists() { command -v "$1" >/dev/null 2>&1; }

sync_host_time_macos() {
  echo "[INFO] macOS: syncing time via sntp/system services"
  if command_exists sntp; then
    sudo sntp -sS time.apple.com || true
  fi
  if command_exists systemsetup; then
    if systemsetup -getusingnetworktime 2>/dev/null | grep -qi "Off"; then
      sudo systemsetup -setusingnetworktime on
      sudo systemsetup -setnetworktimeserver time.apple.com
    fi
  fi
  echo "[OK] macOS time sync attempted. Current time: $(date)"
}

sync_host_time_linux() {
  echo "[INFO] Linux: syncing time via timedatectl/ntpdate/chronyc if available"
  if command_exists timedatectl; then
    sudo timedatectl set-ntp true || true
  fi
  if command_exists chronyc; then
    sudo chronyc -a makestep || true
  elif command_exists ntpdate; then
    sudo ntpdate -u pool.ntp.org || true
  fi
  echo "[OK] Linux time sync attempted. Current time: $(date)"
}

show_container_guidance() {
  cat <<EOF
[INFO] Containers follow the host system time.
- Ensure host time is correct (run: scripts/sync_time.sh)
- If you must set container time directly, the container needs CAP_SYS_TIME and tools installed.
  Example (not generally recommended):
    docker run --cap-add=SYS_TIME --rm alpine sh -c "date -s '@$(date +%s)' && date"
EOF
}

main() {
  mode=${1:-host}
  if [[ "$mode" == "containers" ]]; then
    show_container_guidance
    exit 0
  fi

  unameOut="$(uname -s)"
  case "$unameOut" in
    Darwin*) sync_host_time_macos ;;
    Linux*)  sync_host_time_linux ;;
    *)       echo "[WARN] Unsupported OS: $unameOut. Current time: $(date)" ;;
  esac
}

main "$@"
