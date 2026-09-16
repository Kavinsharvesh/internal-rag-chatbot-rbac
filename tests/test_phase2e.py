import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def run_phase2e_tests():
    print("==================================================")
    print(" RUNNING PHASE 2E END-TO-END RAG /CHAT TESTS ")
    print("==================================================")

    # TEST 1: Tony (engineering) -> "architecture overview"
    print("\n--- TEST 1: Tony (engineering) -> 'architecture overview' ---")
    res1 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "architecture overview"}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["role"] == "engineering"
    assert data1["status"] == "success"
    assert "engineering/engineering_master_doc.md" in data1["sources"]
    assert "Offline retrieval fallback:" in data1["answer"]
    print("PASSED: Tony retrieved engineering document with Offline Retrieval Fallback answer.")

    # TEST 2: Tony (engineering) -> "leave policy"
    print("\n--- TEST 2: Tony (engineering) -> 'leave policy' ---")
    res2 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "leave policy"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["role"] == "engineering"
    assert data2["status"] == "success"
    assert "general/employee_handbook.md" in data2["sources"]
    print("PASSED: Tony retrieved general handbook document.")

    # TEST 3: SECURITY & RELEVANCE: Tony (engineering) -> "quarterly revenue report"
    print("\n--- TEST 3: SECURITY & RELEVANCE: Tony (engineering) -> 'quarterly revenue report' ---")
    res3 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "quarterly revenue report"}
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["role"] == "engineering"
    assert data3["status"] == "no_results"
    assert data3["sources"] == []
    assert "No relevant information was found" in data3["answer"]
    print("PASSED: Tony received status='no_results' and 0 irrelevant engineering/general/finance chunks.")

    # TEST 4: Sam (finance) -> "quarterly revenue report"
    print("\n--- TEST 4: Sam (finance) -> 'quarterly revenue report' ---")
    res4 = client.post(
        "/chat",
        auth=("Sam", "financepass"),
        json={"message": "quarterly revenue report"}
    )
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["role"] == "finance"
    assert data4["status"] == "success"
    assert any("finance/" in src for src in data4["sources"])
    print(f"PASSED: Sam retrieved finance sources -> {data4['sources']}")

    # TEST 5: Natasha (hr) -> "Aadhya Patel HR manager"
    print("\n--- TEST 5: Natasha (hr) -> 'Aadhya Patel HR manager' ---")
    res5 = client.post(
        "/chat",
        auth=("Natasha", "hrpass123"),
        json={"message": "Aadhya Patel HR manager"}
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["role"] == "hr"
    assert data5["status"] == "success"
    assert "hr/hr_data.csv" in data5["sources"]
    assert "salary:" not in data5["answer"].lower()
    print(f"PASSED: Natasha retrieved HR CSV data without salary exposure -> {data5['sources']}")

    # TEST 6: SECURITY: Tony (engineering) -> "salary payroll employee compensation"
    print("\n--- TEST 6: SECURITY: Tony (engineering) -> 'salary payroll employee compensation' ---")
    res6 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "salary payroll employee compensation"}
    )
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["role"] == "engineering"
    for src in data6["sources"]:
        assert not src.startswith("hr/"), f"SECURITY VIOLATION: Found HR source {src}"
    print(f"PASSED: Zero HR sources returned to Tony (Sources returned: {data6['sources']}).")


    # TEST 7: Unauthenticated /chat Request
    print("\n--- TEST 7: Unauthenticated /chat Request ---")
    res7 = client.post("/chat", json={"message": "architecture overview"})
    assert res7.status_code == 401
    print("PASSED: Unauthenticated request rejected with HTTP 401.")

    # TEST 8: Empty / Whitespace Query
    print("\n--- TEST 8: Empty / Whitespace Query ---")
    res8 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "   "}
    )
    assert res8.status_code == 200
    data8 = res8.json()
    assert data8["status"] == "no_results"
    assert data8["sources"] == []
    assert "Please enter a valid query message." in data8["answer"]
    print("PASSED: Empty query handled cleanly without vector search crash.")

    # TEST 9: SECURITY: Role Escalation Attack Prevention
    print("\n--- TEST 9: SECURITY: Role Escalation Attack Prevention ---")
    res9 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "quarterly revenue report", "role": "finance"}
    )
    assert res9.status_code == 200
    data9 = res9.json()
    assert data9["role"] == "engineering", f"Role escalation succeeded! Got {data9['role']}"
    assert data9["status"] == "no_results"
    assert data9["sources"] == []
    print("PASSED: Client-supplied 'role' field ignored; server-side authenticated role enforced.")

    print("\n==================================================")
    print(" ALL 9 PHASE 2E END-TO-END RAG TESTS PASSED! ")
    print("==================================================")


if __name__ == "__main__":
    run_phase2e_tests()
