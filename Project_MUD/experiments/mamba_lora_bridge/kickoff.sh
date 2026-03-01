#!/bin/bash
# kickoff.sh - Launch the Mamba probe in the background robustly

cd /mnt/c/Users/USER/bridge
# Redirect all output and detach from tty to survive SSH closure
nohup bash ./run_probe.sh 300 3,12,24 5 500 > /home/user/probe_output.log 2>&1 < /dev/null &
PID=$!
echo $PID > /home/user/probe.pid
echo "Probe launched in background with PID: $PID"
