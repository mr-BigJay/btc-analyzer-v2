"""Chapter 19 — Security, Authentication & Operational Hardening tests."""

from __future__ import annotations

from src.security.accounts import clear_auth_failures, hash_password, is_locked, record_auth_failure, verify_password
from src.security.audit import AuditTrail
from src.security.contracts import AuditAction, SecurityObject
from src.security.engine import SecurityEngine
from src.security.hardening import apply_security_headers, production_checklist, threat_protections
from src.security.secrets import mask_mapping, mask_secrets


def test_security_object_shape():
    obj = SecurityObject()
    d = obj.to_dict()
    assert d["authentication"] == "JWT"
    assert d["authorization"] == "RBAC"
    assert d["rate_limiting"] is True
    assert d["audit_logging"] is True
    assert d["schema_version"] == "1.0"


def test_mask_secrets_redacts_tokens_and_keys():
    msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.aaa.bbb api_key=supersecret"
    redacted = mask_secrets(msg)
    assert "supersecret" not in redacted
    assert "eyJ" not in redacted or "***JWT***" in redacted
    mapped = mask_mapping({"access_token": "abc", "market_bias": "Bullish"})
    assert mapped["access_token"] == "***REDACTED***"
    assert mapped["market_bias"] == "Bullish"


def test_password_hash_and_verify():
    encoded = hash_password("CorrectHorseBattery")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("CorrectHorseBattery", encoded)
    assert not verify_password("wrong", encoded)


def test_lockout_after_failures():
    identity = "lockout-test-user"
    clear_auth_failures(identity)
    for _ in range(4):
        info = record_auth_failure(identity)
        assert info["locked"] is False
    info = record_auth_failure(identity)
    assert info["locked"] is True
    assert is_locked(identity)
    clear_auth_failures(identity)


def test_audit_trail_append_only():
    trail = AuditTrail(maxlen=20)
    r1 = trail.append(AuditAction.LOGIN, actor="alice", outcome="success", resource="/auth")
    r2 = trail.append(
        AuditAction.AUTH_FAILED,
        actor="bob",
        outcome="failure",
        resource="/auth",
        detail="api_key=secret123",
    )
    assert r1.audit_id != r2.audit_id
    listed = trail.list(limit=10)
    assert listed
    assert "secret123" not in (listed[0].get("detail") or "")


def test_security_headers_applied():
    headers: dict[str, str] = {}
    apply_security_headers(headers, https=True)
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in headers
    assert "Strict-Transport-Security" in headers
    headers2: dict[str, str] = {}
    apply_security_headers(headers2, https=False)
    assert "Strict-Transport-Security" not in headers2


def test_production_checklist_core():
    cl = production_checklist(https_enforced=False, backups_verified=False, dependency_scan=False)
    assert cl["production_ready_core"] is True
    labels = {i["control"] for i in cl["items"]}
    assert "Rate limiting enabled" in labels
    assert "SQL Injection" in threat_protections()


def test_security_engine_status():
    status = SecurityEngine().status()
    assert "Confidentiality" in status["objectives"]
    assert status["security_object"]["authorization"] == "RBAC"
    assert "Detection" in status["incident_lifecycle"]


def test_security_api():
    from fastapi.testclient import TestClient

    from src.api.app import app

    client = TestClient(app)
    r = client.get("/api/v1/security/status")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["security_object"]["authentication"] == "JWT"
    assert body["schema_version"]

    r2 = client.get("/api/v1/security/posture")
    assert r2.status_code == 200
    assert r2.json()["data"]["rate_limiting"] is True

    r3 = client.get("/api/v1/security/checklist")
    assert r3.status_code == 200
    assert r3.json()["data"]["items"]

    client.post("/api/v1/integration/auth/token", json={"subject": "x", "api_key": "bad-key-not-configured"})
    r4 = client.get("/api/v1/security/audit?limit=10")
    assert r4.status_code == 200
    assert "audit" in r4.json()["data"]

    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("content-security-policy")
    assert r.headers.get("referrer-policy") == "no-referrer"
    assert r.headers.get("permissions-policy")
