import sys
from pathlib import Path

# Add project root to sys.path so imports work cleanly from anywhere
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag_service import retrieve_authorized_chunks
from app.services.vector_service import index_documents


def print_test_case(test_num: int, title: str, res: dict):
    user = res["role"].capitalize()
    role = res["role"]
    query = res["query"]
    allowed_depts = res["permitted_departments"]
    where_filter = res["where_filter"]
    returned_depts = sorted(list(set(c["department"] for c in res["chunks"])))
    returned_sources = res["sources"]

    print(f"\n--- TEST {test_num}: {title} ---")
    print(f"User: {user} | Role: {role}")
    print(f"Query: '{query}'")
    print(f"Allowed Departments (RBAC): {allowed_depts}")
    print(f"ChromaDB Pre-Filter Applied: {where_filter}")
    print(f"Returned Departments: {returned_depts}")
    print(f"Returned Sources: {returned_sources}")
    print(f"Status: {res['status']} ({res['message']})")


def run_phase2d_tests():
    print("==================================================")
    print(" RUNNING PHASE 2D SECURE VECTOR RETRIEVAL TESTS ")
    print("==================================================")

    # Ensure vector index exists
    index_documents(reset=False)

    # TEST 1: Tony (engineering) + "architecture overview"
    res1 = retrieve_authorized_chunks("architecture overview", role="engineering")
    print_test_case(1, "Tony (engineering) -> 'architecture overview'", res1)
    assert res1["status"] == "success"
    assert "engineering" in [c["department"] for c in res1["chunks"]]
    print("PASSED: Engineering content successfully retrieved for Tony.")

    # TEST 2: Tony (engineering) + "leave policy"
    res2 = retrieve_authorized_chunks("leave policy", role="engineering")
    print_test_case(2, "Tony (engineering) -> 'leave policy'", res2)
    assert res2["status"] == "success"
    assert "general" in [c["department"] for c in res2["chunks"]]
    print("PASSED: General employee handbook content retrieved for Tony.")

    # TEST 3: Tony (engineering) + "quarterly revenue report" (Security Check)
    res3 = retrieve_authorized_chunks("quarterly revenue report", role="engineering")
    print_test_case(3, "SECURITY: Tony (engineering) -> 'quarterly revenue report'", res3)
    returned_depts3 = set(c["department"] for c in res3["chunks"])
    assert "finance" not in returned_depts3, "SECURITY VIOLATION: Finance chunks returned to Tony!"
    for src in res3["sources"]:
        assert not src.startswith("finance/"), f"SECURITY VIOLATION: Found finance source {src}"
    print("PASSED: Zero finance chunks retrieved for Tony.")

    # TEST 4: Sam (finance) + "quarterly revenue report"
    res4 = retrieve_authorized_chunks("quarterly revenue report", role="finance")
    print_test_case(4, "Sam (finance) -> 'quarterly revenue report'", res4)
    assert res4["status"] == "success"
    assert "finance" in [c["department"] for c in res4["chunks"]]
    print("PASSED: Finance content successfully retrieved for Sam.")

    # TEST 5: Natasha (HR) + "Aadhya Patel HR manager"
    res5 = retrieve_authorized_chunks("Aadhya Patel HR manager", role="hr")
    print_test_case(5, "Natasha (hr) -> 'Aadhya Patel HR manager'", res5)
    assert res5["status"] == "success"
    returned_depts5 = set(c["department"] for c in res5["chunks"])
    assert returned_depts5.issubset(set(res5["permitted_departments"])), "Security error in HR retrieval!"
    assert "hr" in returned_depts5, "Expected HR department chunks for Natasha."
    print("PASSED: HR content successfully retrieved for Natasha.")


    # TEST 6: Tony (engineering) + "salary payroll employee compensation" (Security Check)
    res6 = retrieve_authorized_chunks("salary payroll employee compensation", role="engineering")
    print_test_case(6, "SECURITY: Tony (engineering) -> 'salary payroll employee compensation'", res6)
    returned_depts6 = set(c["department"] for c in res6["chunks"])
    assert "hr" not in returned_depts6, "SECURITY VIOLATION: HR chunks returned to Tony!"
    for src in res6["sources"]:
        assert not src.startswith("hr/"), f"SECURITY VIOLATION: Found HR source {src}"
    print("PASSED: Zero HR chunks retrieved for Tony.")

    # TEST 7: General User + "microservices architecture overview" (Security Check)
    res7 = retrieve_authorized_chunks("microservices architecture overview", role="general")
    print_test_case(7, "SECURITY: General User -> 'microservices architecture overview'", res7)
    returned_depts7 = set(c["department"] for c in res7["chunks"])
    assert "engineering" not in returned_depts7, "SECURITY VIOLATION: Engineering chunks returned to General user!"
    print("PASSED: Engineering content blocked for General user.")

    # TEST 8: ChromaDB Pre-Filter Inspection Verification
    print("\n--- TEST 8: SECURITY ARCHITECTURE CHECK (ChromaDB Pre-Filter Verification) ---")
    res8 = retrieve_authorized_chunks("test query", role="engineering")
    filter_arg = res8["where_filter"]
    print(f"Role: engineering | Filter Object Passed to ChromaDB: {filter_arg}")
    assert filter_arg == {"department": {"$in": ["engineering", "general"]}}, (
        f"Incorrect filter passed to ChromaDB: {filter_arg}"
    )
    print("PASSED: Confirmed ChromaDB query is constrained to permitted departments BEFORE vector similarity search.")

    print("\n==================================================")
    print(" ALL 8 PHASE 2D SECURITY TESTS PASSED! ")
    print("==================================================")


def test_phase2d():
    run_phase2d_tests()


if __name__ == "__main__":
    run_phase2d_tests()
