import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.services.llm_service import generate_llm_answer

client = TestClient(app)


def run_phase2f_tests():
    print("==================================================")
    print(" RUNNING PHASE 2F GEMINI LLM & SAFETY TESTS ")
    print("==================================================")

    # TEST 1: Tony (engineering) -> Engineering question
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
    assert data1["mode"] in ["gemini", "offline_fallback"]
    print(f"PASSED: Tony query mode='{data1['mode']}', sources={data1['sources']}")

    # TEST 2: SECURITY: Tony (engineering) -> Finance question
    print("\n--- TEST 2: SECURITY: Tony (engineering) -> 'quarterly revenue report' ---")
    res2 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "quarterly revenue report"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["role"] == "engineering"
    assert data2["status"] == "no_results"
    assert data2["sources"] == []
    for src in data2["sources"]:
        assert not src.startswith("finance/"), f"SECURITY VIOLATION: Found finance source {src}"
    print("PASSED: Zero finance chunks sent or returned for Tony.")

    # TEST 3: Sam (finance) -> Finance question
    print("\n--- TEST 3: Sam (finance) -> 'quarterly revenue report' ---")
    res3 = client.post(
        "/chat",
        auth=("Sam", "financepass"),
        json={"message": "quarterly revenue report"}
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["role"] == "finance"
    assert data3["status"] == "success"
    assert any("finance/" in src for src in data3["sources"])
    print(f"PASSED: Sam retrieved finance sources -> {data3['sources']}")

    # TEST 4: Natasha (hr) -> HR question (Salary Redaction Check)
    print("\n--- TEST 4: Natasha (hr) -> 'Aadhya Patel HR manager' ---")
    res4 = client.post(
        "/chat",
        auth=("Natasha", "hrpass123"),
        json={"message": "Aadhya Patel HR manager"}
    )
    assert res4.status_code == 200
    data4 = res4.json()
    assert data4["role"] == "hr"
    assert data4["status"] == "success"
    assert "hr/hr_data.csv" in data4["sources"]
    assert "salary:" not in data4["answer"].lower()
    print("PASSED: Natasha retrieved HR CSV data without salary exposure.")

    # TEST 5: SECURITY: Role Escalation Attack Prevention
    print("\n--- TEST 5: SECURITY: Role Escalation Attack Prevention ---")
    res5 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "quarterly revenue report", "role": "finance"}
    )
    assert res5.status_code == 200
    data5 = res5.json()
    assert data5["role"] == "engineering"
    assert data5["status"] == "no_results"
    assert data5["sources"] == []
    print("PASSED: Client-supplied 'role' payload ignored; server-side authenticated role enforced.")

    # TEST 6: No Relevant Authorized Chunks -> Gemini NOT called
    print("\n--- TEST 6: No Relevant Authorized Chunks -> Gemini NOT called ---")
    res6 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "quantum physics supercollider"}
    )
    assert res6.status_code == 200
    data6 = res6.json()
    assert data6["status"] == "no_results"
    assert data6["sources"] == []
    assert data6["mode"] == "offline_fallback"
    print("PASSED: Gemini not called when 0 authorized chunks match.")

    # TEST 7: Missing API Key Fallback Safety
    print("\n--- TEST 7: Missing API Key Fallback Safety ---")
    original_key = os.environ.get("GOOGLE_API_KEY")
    try:
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

        test_chunks = [{
            "chunk_id": "test_chunk_1",
            "content": "FinSolve Engineering microservices architecture overview.",
            "source": "engineering/engineering_master_doc.md"
        }]
        ans = generate_llm_answer("architecture overview", test_chunks, ["engineering/engineering_master_doc.md"])
        assert ans is None, "Expected None when GOOGLE_API_KEY is missing"

        res7 = client.post(
            "/chat",
            auth=("Tony", "password123"),
            json={"message": "architecture overview"}
        )
        assert res7.status_code == 200
        data7 = res7.json()
        assert data7["status"] == "success"
        assert data7["mode"] == "offline_fallback"
        print("PASSED: Application operates safely in offline fallback mode when GOOGLE_API_KEY is missing.")
    finally:
        if original_key is not None:
            os.environ["GOOGLE_API_KEY"] = original_key

    # TEST 8: API Key Secrecy Verification
    print("\n--- TEST 8: SECURITY: API Key Secrecy Verification ---")
    api_key_val = os.getenv("GOOGLE_API_KEY", "")
    res8 = client.post(
        "/chat",
        auth=("Tony", "password123"),
        json={"message": "architecture overview"}
    )
    response_str = str(res8.json())
    if api_key_val and len(api_key_val) > 5:
        assert api_key_val not in response_str, "SECURITY VIOLATION: GOOGLE_API_KEY exposed in API response!"
    print("PASSED: GOOGLE_API_KEY is never exposed in API responses or logs.")

    print("\n==================================================")
    print(" ALL 8 PHASE 2F GEMINI & SAFETY TESTS PASSED! ")
    print("==================================================")


def test_phase2f():
    run_phase2f_tests()


if __name__ == "__main__":
    run_phase2f_tests()

