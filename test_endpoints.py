import urllib.request
import json
import sys

# Force UTF-8 output on Windows to avoid UnicodeEncodeError for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


BASE_URL = "http://localhost:8000"


def make_request(method, path, body=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8") if body else None,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))
    except Exception as e:
        return 500, {"error": str(e)}


def test_endpoints():
    print("=== Testing Root Endpoint ===")
    status, res = make_request("GET", "/")
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Root endpoint failed"
    assert "health" in res, "Invalid root response structure"

    print("\n=== Testing Health Check ===")
    status, res = make_request("GET", "/api/health")
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Health check failed"
    assert res.get("status") == "healthy", "App unhealthy"

    print("\n=== Testing Chat (Greeting Stage) ===")
    status, res = make_request("POST", "/api/chat", {"message": "hello"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Greeting test failed"
    assert res.get("response_type") == "greeting", "Should route to greeting"

    print("\n=== Testing Chat (Static Stage - Location) ===")
    status, res = make_request("POST", "/api/chat", {"message": "where is AITD kanpur"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Static Location test failed"
    assert res.get("response_type") == "static", "Should route to static"

    print("\n=== Testing Chat (Static Stage - Developer) ===")
    status, res = make_request("POST", "/api/chat", {"message": "who created you"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Static Developer test failed"
    assert res.get("response_type") == "static", "Should route to static"

    print("\n=== Testing Chat (Static Stage - Contact) ===")
    status, res = make_request("POST", "/api/chat", {"message": "what is the contact number"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Static Contact test failed"
    assert res.get("response_type") == "static", "Should route to static"

    print("\n=== Testing Chat (FAQ Stage) ===")
    status, res = make_request("POST", "/api/chat", {"message": "what is the hostel fee?"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "FAQ test failed"
    assert res.get("response_type") == "faq", "Should route to FAQ"

    print("\n=== Testing Chat (Out-of-Scope Stage) ===")
    status, res = make_request("POST", "/api/chat", {"message": "who won IPL yesterday?"})
    print(f"Status: {status}")
    print("Response:", res)
    assert status == 200, "Out-of-scope test failed"
    assert res.get("response_type") == "out_of_scope", "Should be out of scope"

    print("\n[SUCCESS] All core backend endpoints verified successfully!")


if __name__ == "__main__":
    test_endpoints()
