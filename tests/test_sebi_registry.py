# tests/test_sebi_registry.py
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from apps.api.app.services.sebi_registry import (
    StaticIPAllocationPool,
    SebiComplianceRegistry,
    SebiRARegistrationRequest,
)


def test_sebi_compliance_registry():
    print("[+] Testing SebiComplianceRegistry & StaticIPAllocationPool...")

    # 1. Test Static IP 1:1 allocation
    pool = StaticIPAllocationPool()
    ip_u1 = pool.allocate_static_ip_for_user("usr_01")
    ip_u2 = pool.allocate_static_ip_for_user("usr_02")
    assert ip_u1 == "13.232.104.1"
    assert ip_u2 == "13.232.104.2"
    # Idempotency check: same user gets identical IP
    assert pool.allocate_static_ip_for_user("usr_01") == "13.232.104.1"
    print(f"  [OK] 1:1 Static IP Allocation verified: usr_01 -> {ip_u1}, usr_02 -> {ip_u2}")

    # 2. Test Successful RA Registration
    dummy_pdf = b"%PDF-1.4 Mock SEBI Research Analyst Certificate INH000016402"
    req_valid = SebiRARegistrationRequest(
        creator_id="creator_ra_1",
        legal_entity_name="AlphaEdge Capital LLP",
        sebi_ra_registration_number="INH000016402",
        research_report_pdf_bytes=dummy_pdf,
        declared_static_ip="13.232.104.1",  # Matches first allocation in global pool
    )
    res_valid = SebiComplianceRegistry.verify_and_register_creator(req_valid)
    assert res_valid.verification_status == "VERIFIED_ACTIVE"
    assert len(res_valid.pdf_sha256_audit_hash) == 64
    assert res_valid.assigned_nat_static_ip == "13.232.104.1"
    print(f"  [OK] Valid SEBI RA Verified: {res_valid.sebi_ra_number}, PDF SHA-256: {res_valid.pdf_sha256_audit_hash[:16]}...")

    # 3. Test IP Mismatch Rejection
    req_mismatch = SebiRARegistrationRequest(
        creator_id="creator_ra_2",
        legal_entity_name="Rogue Trading Inc",
        sebi_ra_registration_number="INH000099999",
        research_report_pdf_bytes=dummy_pdf,
        declared_static_ip="1.2.3.4",  # Discrepancy with assigned pool IP
    )
    res_mismatch = SebiComplianceRegistry.verify_and_register_creator(req_mismatch)
    assert res_mismatch.verification_status == "REJECTED_INVALID_LICENSE"
    print("  [OK] Declared IP discrepancy correctly rejected with REJECTED_INVALID_LICENSE.")

    print("ALL SEBI COMPLIANCE REGISTRY TESTS PASSED!")


if __name__ == "__main__":
    test_sebi_compliance_registry()
