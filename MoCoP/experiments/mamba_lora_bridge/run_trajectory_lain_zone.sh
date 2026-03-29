cd /mnt/c/Users/tikii/bridge
/root/mocop_venv/bin/python3 -X utf8 trajectory_sequential.py \
  --conversation-json lucian_conversations.json \
  --conv-index 35 \
  --max-messages 1670 \
  --sample-every 50 \
  --method tokenwise \
  --output-dir /mnt/c/Users/tikii/bridge/trajectory_lain_zone \
  --device cuda
