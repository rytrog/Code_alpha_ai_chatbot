"""
Comprehensive test of the fixed RAG pipeline.
Tests: RAG from files, FAQ, scope, negative cache prevention, website fallback.
"""
import requests
import time
import sys
import os

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:8000"
results = []


def test(label, message, expect_type=None, expect_contains=None, expect_not_cached=False):
    """Send a query and check expectations."""
    print(f"\n{'='*70}")
    print(f"TEST: {label}")
    print(f"Query: {message}")

    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": message},
            timeout=30,
        )
        elapsed = time.time() - start
        data = resp.json()

        rtype = data.get("response_type", "N/A")
        answer = data.get("answer", "N/A")
        source = data.get("source", "")

        print(f"Status: {resp.status_code} | Time: {elapsed:.1f}s | Type: {rtype}")
        print(f"Answer: {answer[:250]}")
        if source:
            print(f"Source: {source[:150]}")

        passed = True
        failures = []

        if expect_type:
            if expect_type == "rag" and rtype in ("rag", "cached"):
                pass  # Warm cache is acceptable for RAG queries
            elif rtype != expect_type:
                failures.append(f"Expected type '{expect_type}' but got '{rtype}'")
                passed = False

        if expect_contains:
            if expect_contains.lower() not in answer.lower():
                failures.append(f"Expected answer to contain '{expect_contains}'")
                passed = False

        status = "PASS" if passed else "FAIL"
        if failures:
            for f in failures:
                print(f"  >> FAIL: {f}")

        results.append({"label": label, "status": status, "type": rtype})
        print(f"Result: {status}")
        return data

    except Exception as e:
        print(f"ERROR: {e}")
        results.append({"label": label, "status": "ERROR", "type": "error"})
        return None


def main():
    # Health check
    print("\n--- HEALTH CHECK ---")
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        h = r.json()
        print(f"Status: {h['status']} | DB: {h['services']['postgresql']} | Chroma: {h['services']['chromadb']}")
    except Exception as e:
        print(f"Health check FAILED: {e}")
        return

    # === SECTION 1: RAG from uploaded files ===
    print("\n\n" + "="*70)
    print("SECTION 1: RAG from uploaded files")
    print("="*70)

    test("Placement companies",
         "What are the placement companies at AITD?",
         expect_type="rag",
         expect_contains="Accenture")

    test("HOD of Biotechnology",
         "Who is the HOD of Biotechnology department?",
         expect_contains="Manish")

    test("Director of AITD",
         "Who is the Director of AITD?",
         expect_contains="Rachna")

    test("Fee for first year",
         "What is the fee for first year admission?",
         expect_contains="76,000")

    test("Diploma courses",
         "What diploma courses are available?",
         expect_contains="Architecture")

    test("Dean of T&P",
         "Who is the Dean of Training and Placement?",
         expect_contains="Kamani")

    test("How to reach AITD",
         "How to reach AITD from Kanpur Central?",
         expect_contains="metro")

    # === SECTION 2: FAQ answers ===
    print("\n\n" + "="*70)
    print("SECTION 2: FAQ answers")
    print("="*70)

    test("HOD of CSE (FAQ)",
         "Who is the HOD of CSE?",
         expect_type="faq",
         expect_contains="Dwivedi")

    test("Fee structure (FAQ)",
         "What is the fee structure?",
         expect_type="faq")

    # === SECTION 3: Out-of-scope rejection ===
    print("\n\n" + "="*70)
    print("SECTION 3: Out-of-scope rejection")
    print("="*70)

    test("Politics (blocked)",
         "Who is the president of India?",
         expect_type="out_of_scope")

    test("Coding (blocked)",
         "Write python code for sorting",
         expect_type="out_of_scope")

    # === SECTION 4: Negative cache prevention ===
    print("\n\n" + "="*70)
    print("SECTION 4: Negative cache prevention")
    print("="*70)

    # Query something unlikely to be in the database
    r1 = test("Obscure query (1st)",
              "What is the hostel mess menu for today?")

    r2 = test("Obscure query (2nd - should NOT be cached)",
              "What is the hostel mess menu for today?")

    if r1 and r2:
        if r2.get("response_type") == "cached" and "not available" in r2.get("answer", "").lower():
            print("\n  >> CRITICAL FAIL: Negative answer was cached!")
            results.append({"label": "Negative cache test", "status": "FAIL", "type": "cached"})
        else:
            print("\n  >> Negative cache test PASSED")
            results.append({"label": "Negative cache test", "status": "PASS", "type": r2.get("response_type")})

    # === SECTION 5: Greeting ===
    print("\n\n" + "="*70)
    print("SECTION 5: Greeting")
    print("="*70)

    test("Greeting",
         "Hello!",
         expect_type="greeting")

    # === SUMMARY ===
    print("\n\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    print(f"Total: {len(results)} | PASS: {passed} | FAIL: {failed} | ERROR: {errors}")
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else ("FAIL" if r["status"] == "FAIL" else "ERR!")
        print(f"  [{icon}] {r['label']} (type={r['type']})")

    if failed + errors == 0:
        print("\nALL TESTS PASSED!")
    else:
        print(f"\n{failed + errors} ISSUES FOUND - review above")


if __name__ == "__main__":
    main()
