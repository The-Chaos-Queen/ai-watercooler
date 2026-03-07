import os
import winremote
from inspect import getmembers, isfunction

mcp_server_path = os.path.join(os.path.dirname(winremote.__file__), "mcp_server.py")
with open(mcp_server_path, 'r', encoding='utf-8') as f:
    print(f.read())
