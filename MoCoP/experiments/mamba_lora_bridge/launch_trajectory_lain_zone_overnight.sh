set -euo pipefail

cd /mnt/c/Users/tikii/bridge
mkdir -p trajectory_lain_zone

log="/mnt/c/Users/tikii/bridge/trajectory_lain_zone/trajectory_lain_zone.log"
touch "$log"
nohup /root/mocop_venv/bin/python3 -X utf8 trajectory_sequential.py \
  --conversation-json lucian_conversations.json \
  --conv-index 35 \
  --max-messages 1670 \
  --sample-every 50 \
  --method tokenwise \
  --output-dir /mnt/c/Users/tikii/bridge/trajectory_lain_zone \
  --device cuda > "$log" 2>&1 < /dev/null &
echo "started trajectory_lain_zone pid=$! log=$log"
