import os
import winremote

cli_path = os.path.join(os.path.dirname(winremote.__file__), "cli.py")
server_path = os.path.join(os.path.dirname(winremote.__file__), "server.py")
print("Reading:", cli_path)
if os.path.exists(cli_path):
    with open(cli_path, 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print("No cli.py!")

print("Reading:", server_path)
if os.path.exists(server_path):
    with open(server_path, 'r', encoding='utf-8') as f:
        print(f.read())
else:
    print("No server.py!")
