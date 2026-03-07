import os
config_dir = os.path.expanduser('~/.config/winremote')
os.makedirs(config_dir, exist_ok=True)
config_path = os.path.join(config_dir, 'winremote.toml')
print("Writing config to", config_path)
config_content = """[server]
host = "0.0.0.0"
port = 8090
auth_key = ""

[security]
ip_allowlist = ["127.0.0.1", "192.168.2.0/24"]
enable_tier3 = false
disable_tier2 = false

[tools]
enable = []
exclude = []
"""
with open(config_path, 'w', encoding='utf-8') as f:
    f.write(config_content)

print("Running install task...")
os.system("winremote-mcp install")
print("Done.")
