#!/bin/sh

mosquitto -d

python -u /tmp/src/manager.py > /tmp/src/1.log 2>&1 &
