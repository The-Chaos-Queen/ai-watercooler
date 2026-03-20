#!/bin/bash
nohup bash /mnt/c/Users/tikii/steve_download_models.sh > /tmp/model_download.log 2>&1 &
echo "PID=$!"
echo "Log: /tmp/model_download.log"
