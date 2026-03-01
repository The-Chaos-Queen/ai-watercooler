import os
import sys
import importlib.util

spec = importlib.util.find_spec("winremote")
if spec:
    base_dir = os.path.dirname(spec.origin)
    print("Base dir:", base_dir)
    for fname in os.listdir(base_dir):
        if fname.endswith(".py"):
            with open(os.path.join(base_dir, fname), "r", encoding="utf-8") as f:
                content = f.read()
                if "FastMCP" in content or "mcp =" in content or "mcp.run" in content:
                    print(f"--- {fname} ---")
                    for i, line in enumerate(content.splitlines()):
                        if "FastMCP" in line or "mcp." in line or "mcp=" in line.replace(" ", ""):
                            print(f"L{i}: {line.strip()}")
            
else:
    print("winremote not found!")
