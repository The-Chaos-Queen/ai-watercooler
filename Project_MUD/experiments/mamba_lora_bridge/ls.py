import os
import winremote
import sys

base = os.path.dirname(winremote.__file__)
print("Found winremote at:", base)
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            print(path)
            with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                if "FastMCP" in content or "mcp =" in content or "create_mcp" in content:
                    print("--> FOUND IN", f)
                    for i, line in enumerate(content.splitlines()):
                        if "FastMCP" in line or "create_mcp" in line or "mcp" in line.split("=")[0]:
                            print(f"  {i}: {line.strip()}")
