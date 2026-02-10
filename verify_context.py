import requests
import json
import sys

# Authentication (mocking or using valid token if possible, but for local dev with no auth on this endpoint or using the same method as test_stream.ps1)
# The test_stream.ps1 uses a token. We can simulate the request if we have a token, or just rely on the fact that we are running locally and might need to skip auth if it's disabled or standard "Bearer token" flow.
# Actually, the endpoint requires a token.
# Let's just use the `requests` library to hit the endpoint. We need a token.
# I'll rely on the existing token logic or just assuming the local dev environment might have a valid token or I can generate one.
# Wait, `test_stream.ps1` gets a token. I can probably just reuse the logic or simpler:
# I will output the *response* of the test script to a file and parse that? No, that's messy.
# I will use the `requests` library and `app.core.security` to generate a token if I can import it, or just use a hardcoded one if valid.
# Better yet: I will use the `test_stream.ps1` but modify it to PRINT the full JSON body so I can see it.

# Actually, let's just use python to hit valid endpoint.
try:
    from app.core.security import create_access_token
    token = create_access_token({"sub": "admin@example.com"})
    headers = {"Authorization": f"Bearer {token}"}
except ImportError:
    # If I can't import, I'll just use a placeholder and hope it works or fails with 401
    print("Could not import create_access_token")
    sys.exit(1)

url = "http://127.0.0.1:8080/api/executive-report-stream?period=2025&sections=headline"

print(f"Testing URL: {url}")
try:
    with requests.post(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    try:
                        data = json.loads(json_str)
                        # Print relevant parts
                        section_id = data.get("section_id")
                        print(f"--- Section: {section_id} ---")
                        for block in data.get("blocks", []):
                            if block.get("type") == "text" and block.get("variant") in ["h2", "h3", "insight"]:
                                print(f"[{block.get('variant')}] {block.get('payload')[:100]}...")
                    except json.JSONDecodeError:
                        print(f"Could not decode JSON: {json_str[:50]}...")
except Exception as e:
    print(f"Request failed: {e}")
