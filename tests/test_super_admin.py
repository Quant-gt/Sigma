# tests/test_super_admin.py
import sys
import os
import asyncio
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath("."))
from apps.api.main import app

client = TestClient(app)


def test_super_admin_citadel_pipeline():
    print("[+] Testing SigmaSpire Staff Citadel & Chinese Wall API...")

    # 1. Test Hardware MFA Authentication
    auth_res = client.post(
        "/api/v1/super-admin/auth/mfa-verify",
        json={
            "staffEmail": "admin@sigmaspire.internal",
            "hardwarePasskeyId": "YUBIKEY_FIDO2_SECURE_9941",
            "totpCode": "849201",
            "sessionClientIp": "127.0.0.1"
        }
    )
    assert auth_res.status_code == 200, f"MFA failed: {auth_res.text}"
    auth_data = auth_res.json()
    assert auth_data["success"] is True
    assert auth_data["role"] == "SUPER_ADMIN"
    staff_token = auth_data["staffToken"]
    print("  [OK] Hardware MFA Verified. Role: SUPER_ADMIN, Token:", staff_token[:16])

    # 2. Test Citadel Live Telemetry
    telemetry_res = client.get(
        "/api/v1/super-admin/citadel/telemetry",
        headers={"X-Staff-Token": staff_token}
    )
    assert telemetry_res.status_code == 200
    telemetry_data = telemetry_res.json()
    assert telemetry_data["activeBrokersOnline"] == 6
    assert telemetry_data["sebiNineOpsThrottleAdherencePct"] == 100.0
    assert len(telemetry_data["trinityComponents"]) == 3
    print("  [OK] Trinity Engine Telemetry Online. 6 Brokers, 100% SEBI 9-OPS Adherence.")

    # 3. Test Chinese Wall Isolation Audit
    cw_res = client.post("/api/v1/super-admin/chinese-wall/audit")
    assert cw_res.status_code == 200
    cw_data = cw_res.json()
    assert cw_data["propAlphaIsolated"] is True
    assert cw_data["retailRoutingIsolated"] is True
    assert cw_data["sharedStateLeakageDetected"] is False
    print("  [OK] Chinese Wall Audit Verified. Zero State Leakage Detected.")

    # 4. Test Global Master Circuit Breaker
    freeze_res = client.post("/api/v1/super-admin/citadel/global-freeze")
    assert freeze_res.status_code == 200
    freeze_data = freeze_res.json()
    assert freeze_data["status"] == "GLOBAL_FREEZE_EXECUTED"
    assert freeze_data["allPipesHalted"] is True
    print("  [OK] Master Circuit Breaker Functional. All 6 broker pipelines halted atomically.")

    # 5. Test Citadel Zero-Trust HMAC Login
    citadel_login = client.post(
        "/api/v1/citadel/auth/login",
        json={
            "staff_email": "admin@sigmaspire.com",
            "password": "SigmaSpire#Citadel2026!",
            "totp_code": "202699",
            "hardware_key_signature": "YUBIKEY_FIDO2_OK"
        }
    )
    assert citadel_login.status_code == 200, f"Citadel login failed: {citadel_login.text}"
    citadel_token = citadel_login.json()["token"]
    print("  [OK] Citadel HMAC Auth Verified. Token:", citadel_token[:20])

    # 6. Test Trinity Alpha Factory Synthesis
    trinity_res = client.post(
        "/api/v1/citadel/trinity/synthesize",
        headers={"x-citadel-token": citadel_token},
        json={
            "underlying": "NIFTY",
            "academic_paper_source": "PAPER_01_ORNSTEIN_UHLENBECK_VOL_CARRY",
            "vibe_customization_prompt": "Adapt for Nifty Weekly with 50 bps MPP"
        }
    )
    assert trinity_res.status_code == 200, f"Trinity synthesis failed: {trinity_res.text}"
    trinity_data = trinity_res.json()
    assert "TRINITY-" in trinity_data["pipeline_id"]
    assert trinity_data["step4_shadow_stress_metrics"]["vibe_shadow_slippage_survival_score"] == 94.2
    print("  [OK] Trinity Alpha Factory Synthesis Passed. Extracted factor & AST generated.")

    # 7. Test Blindfolded Chinese Wall Telemetry
    ops_res = client.get(
        "/api/v1/citadel/ops/telemetry",
        headers={"x-citadel-token": citadel_token}
    )
    assert ops_res.status_code == 200
    ops_data = ops_res.json()
    assert ops_data["chinese_wall_status"] == "ENFORCED_PRIVATE_ASTS_BLINDFOLDED"
    assert ops_data["sebi_static_ip_pool"]["shared_ip_violations"] == 0
    print("  [OK] Blindfolded Chinese Wall Ops Telemetry Verified (0 IP violations).")

    print("ALL SUPER ADMIN & CITADEL TESTS PASSED!")


if __name__ == "__main__":
    test_super_admin_citadel_pipeline()
