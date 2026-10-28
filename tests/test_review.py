import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
import main as brandlens


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(brandlens, "DATABASE_URL", "")
    monkeypatch.setattr(brandlens, "DB_PATH", tmp_path / "brandlens-test.db")
    brandlens.init_db()
    with TestClient(brandlens.app) as test_client:
        yield test_client


def create_account(client, *, name="Test User", invite_code=""):
    email = f"tester-{uuid.uuid4().hex[:10]}@example.com"
    response = client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": "A-secure-test-password-123",
        "invite_code": invite_code,
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    return payload, {"Authorization": f"Bearer {payload['token']}"}


def test_problematic_copy_flags_claims_and_terminology():
    findings = brandlens.analyze_content(
        "LUMALEAF'S MIRACLE SERUM IS 100% SUSTAINABLE!!! It is clinically proven to cure acne fast. Our chemical-free formula delivers guaranteed results.",
        brandlens.SEED_RULES,
        brandlens.SEED_FACTS,
    )
    titles = {finding["title"] for finding in findings}
    assert "Avoid the phrase 'chemical-free'" in titles
    assert "Environmental claims require evidence" in titles
    assert "Medical claims are not approved" in titles
    assert "Avoid guarantees and instant-result promises" in titles
    assert "Use a calm, informative voice" in titles


def test_approved_example_avoids_seeded_claim_flags():
    findings = brandlens.analyze_content(
        "Build a straightforward skincare routine with LumaLeaf. Calm Cleanser contains 2% niacinamide. Our refill pouch uses 70% less packaging plastic by weight than the standard 250 ml bottle.",
        brandlens.SEED_RULES,
        brandlens.SEED_FACTS,
    )
    assert not findings


def test_every_seed_rule_has_a_source():
    for rule in brandlens.SEED_RULES:
        assert rule["source_title"].strip()
        assert rule["source_section"].strip()
        assert rule["source_excerpt"].strip()


def test_protected_routes_require_authentication(client):
    assert client.get("/api/reviews").status_code == 401
    assert client.get("/api/rules").status_code == 401


def test_review_workflow_persists_decision_and_history(client):
    account, admin_headers = create_account(client)
    assert account["user"]["role"] == "brand_admin"

    created = client.post("/api/reviews", headers=admin_headers, json={
        "content": "This is a chemical-free product with guaranteed results.",
        "channel": "Website",
    })
    assert created.status_code == 200, created.text
    review = created.json()
    assert review["findings"]
    assert review["status"] == "pending"
    review_id = review["id"]

    decision = client.post(f"/api/reviews/{review_id}/decision", headers=admin_headers, json={
        "decision": "needs_revision", "reviewer": "Ignored client role", "comment": "Please revise the claim."
    })
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "needs_revision"
    assert decision.json()["decisions"][0]["reviewer"] == account["user"]["name"]

    loaded = client.get(f"/api/reviews/{review_id}", headers=admin_headers)
    assert loaded.status_code == 200
    assert loaded.json()["decisions"]
    history = client.get("/api/reviews", headers=admin_headers).json()["items"]
    assert any(item["id"] == review_id for item in history)


def test_invited_member_joins_workspace_and_roles_are_enforced(client):
    admin, admin_headers = create_account(client, name="Workspace Admin")
    invite_code = admin["user"]["invite_code"]
    member, member_headers = create_account(client, name="Reviewer Candidate", invite_code=invite_code)
    assert member["user"]["workspace_id"] == admin["user"]["workspace_id"]
    assert member["user"]["role"] == "content_creator"

    created = client.post("/api/reviews", headers=admin_headers, json={
        "content": "A chemical-free formula with guaranteed results.", "channel": "Website"
    })
    review_id = created.json()["id"]
    assert client.get("/api/reviews", headers=member_headers).json()["count"] == 1

    denied = client.post(f"/api/reviews/{review_id}/decision", headers=member_headers, json={"decision": "approved"})
    assert denied.status_code == 403

    team = client.get("/api/team", headers=admin_headers)
    assert team.status_code == 200
    update = client.patch(f"/api/team/users/{member['user']['id']}/role", headers=admin_headers, json={"role": "brand_reviewer"})
    assert update.status_code == 200
    accepted = client.post(f"/api/reviews/{review_id}/decision", headers=member_headers, json={"decision": "approved"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"


def test_workspaces_are_isolated(client):
    _, first_headers = create_account(client, name="First Workspace")
    _, second_headers = create_account(client, name="Second Workspace")
    response = client.post("/api/reviews", headers=first_headers, json={
        "content": "This chemical-free formula has guaranteed results.", "channel": "Website"
    })
    review_id = response.json()["id"]
    assert client.get("/api/reviews", headers=second_headers).json()["count"] == 0
    assert client.get(f"/api/reviews/{review_id}", headers=second_headers).status_code == 404


def test_invalid_password_registration_is_rejected(client):
    response = client.post("/api/auth/register", json={
        "name": "Weak Password", "email": "weak@example.com", "password": "password"
    })
    assert response.status_code == 422


def test_login_restores_workspace_and_persistent_review_history(client):
    account, headers = create_account(client, name="Login Test")
    created = client.post("/api/reviews", headers=headers, json={
        "content": "This chemical-free product offers guaranteed results.", "channel": "Website"
    })
    assert created.status_code == 200
    review_id = created.json()["id"]

    login = client.post("/api/auth/login", json={
        "email": account["user"]["email"], "password": "A-secure-test-password-123"
    })
    assert login.status_code == 200
    refreshed_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    me = client.get("/api/auth/me", headers=refreshed_headers)
    assert me.status_code == 200
    assert me.json()["user"]["workspace_id"] == account["user"]["workspace_id"]
    history = client.get("/api/reviews", headers=refreshed_headers).json()["items"]
    assert any(review["id"] == review_id for review in history)

    bad_login = client.post("/api/auth/login", json={
        "email": account["user"]["email"], "password": "incorrect-password"
    })
    assert bad_login.status_code == 401


def test_demo_access_requires_no_signup_and_supports_the_review_workflow(client):
    demo = client.post("/api/auth/demo")
    assert demo.status_code == 200, demo.text
    payload = demo.json()
    assert payload["user"]["is_demo"] is True
    assert payload["user"]["role"] == "brand_reviewer"
    headers = {"Authorization": f"Bearer {payload['token']}"}

    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["is_demo"] is True
    assert client.get("/api/rules", headers=headers).json()["count"] >= 5

    created = client.post("/api/reviews", headers=headers, json={
        "content": "Our chemical-free serum is 100% sustainable and delivers guaranteed results.",
        "channel": "Instagram",
    })
    assert created.status_code == 200, created.text
    review = created.json()
    assert review["findings"]

    decision = client.post(
        f"/api/reviews/{review['id']}/decision",
        headers=headers,
        json={"decision": "approved", "comment": "Approved in demo."},
    )
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "approved"

    # A guest gets an isolated workspace so visitors cannot see or overwrite one another's data.
    second_demo = client.post("/api/auth/demo")
    second_headers = {"Authorization": f"Bearer {second_demo.json()['token']}"}
    assert client.get("/api/reviews", headers=second_headers).json()["count"] == 0
    assert client.get("/api/team", headers=headers).status_code == 403
