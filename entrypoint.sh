#!/usr/bin/env bash

function checkVar {
  if [[ -z "${!1}" ]]; then
    echo "FATAL: Environment variable $1 must be defined"
    exit 1
  fi
}

checkVar "N7_USERNAME"
checkVar "N7_PASSWORD"
checkVar "BOT_SECRET"

echo "Creating a fake display for Firefox"
Xvfb :1 -screen 0 1920x1080x16 &
sleep 10

echo "Starting main script"
python3 main.py

