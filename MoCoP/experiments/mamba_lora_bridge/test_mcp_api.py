import requests
import json
import time

url = "http://192.168.2.194:8090/mcp"
print(f"Connecting to MCP SSE endpoint {url}...")

try:
    with requests.get(url, stream=True, timeout=10, headers={'Accept': 'text/event-stream'}) as r:
        r.raise_for_status()
        post_endpoint = None
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print("SSE:", decoded_line)
                if decoded_line.startswith("event: endpoint"):
                    # The next line should be 'data: /endpoint'
                    pass
                elif decoded_line.startswith("data:") and "/message" in decoded_line:
                    post_endpoint = decoded_line.replace("data:", "").strip()
                    break

        if not post_endpoint:
            print("Failed to get endpoint from SSE stream.")
            exit(1)

        if not post_endpoint.startswith("http"):
            # Construct full URL if relative
            post_url = f"http://192.168.2.194:8090{post_endpoint}"
        else:
            post_url = post_endpoint

        print(f"Got message endpoint: {post_url}")
        
        # Test 1: Initialize
        msg_init = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05", # standard current MCP version
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        res = requests.post(post_url, json=msg_init)
        print("Init HTTP Status:", res.status_code)

        # Let the SSE stream process logic
        time.sleep(1) 

        # Call Notification
        msg_init_notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        requests.post(post_url, json=msg_init_notif)

        time.sleep(1)
        
        # Test 2: Call the 'Shell' tool
        msg_call = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "Shell",
                "arguments": {
                    "command": "start powershell"
                }
            }
        }
        res = requests.post(post_url, json=msg_call)
        print("Call HTTP Status:", res.status_code)
        print("MCP execution initiated. Terminal should now open on Opa-PC!")

except Exception as e:
    print("Error:", str(e))
