#!/bin/bash
echo "=== RAM ==="
free -h
echo "=== dmesg OOM ==="
dmesg 2>/dev/null | grep -i "oom\|killed" | tail -5 || echo "no dmesg access"
echo "=== journalctl OOM ==="
journalctl -k 2>/dev/null | grep -i "oom\|killed" | tail -5 || echo "no journalctl"
