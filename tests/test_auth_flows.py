import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException


@pytest.fixture()
def auth_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "auth_flows_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("AUTO_INIT_DB", "true")
    monkeypatch.setenv("STRICT_MIGRATIONS", "false")
    monkeypatch.setenv("USE_DB_AUTH", "true")

    import database.session as session_module
    import database.models as models_module
    import scripts.auth as auth_module

    session_module = importlib.reload(session_module)
    models_module = importlib.reload(models_module)
    models_module.Base.metadata.create_all(bind=session_module.engine)
    auth_module = importlib.reload(auth_module)
    auth_module.init_auth_storage()

    yield auth_module

    models_module.Base.metadata.drop_all(bind=session_module.engine)


def test_refresh_token_rotation(auth_env):
    auth = auth_env

    user = auth.authenticate_user(auth.DEFAULT_ADMIN_EMAIL, "admin123")
    assert user is not None
    assert user.get("user_id") is not None

    refresh = auth.create_refresh_token(user_id=int(user["user_id"]))
    access, new_refresh = auth.refresh_access_token(refresh)

    assert isinstance(access, str) and len(access) > 20
    assert isinstance(new_refresh, str) and len(new_refresh) > 20

    with pytest.raises(Exception):
        auth.refresh_access_token(refresh)


def test_invite_accept_flow_creates_membership(auth_env):
    auth = auth_env

    admin = auth.get_user_claims(auth.DEFAULT_ADMIN_EMAIL)
    assert admin is not None

    invite_token = auth.create_user_invite(actor=admin, email="new.member@complyai.io", role="analyst")
    claims = auth.accept_user_invite(
        invite_token=invite_token,
        full_name="New Member",
        password="StrongPass123!",
    )

    assert claims["email"] == "new.member@complyai.io"
    assert claims["org_id"] == admin["org_id"]
    assert claims["role"] == "analyst"


def test_login_lockout_triggers_after_threshold(auth_env):
    auth = auth_env

    for _ in range(auth.MAX_LOGIN_ATTEMPTS):
        auth.register_login_failure(auth.DEFAULT_ADMIN_EMAIL)

    with pytest.raises(HTTPException) as exc:
        auth.assert_login_not_locked(auth.DEFAULT_ADMIN_EMAIL)

    assert exc.value.status_code == 423


def test_require_roles_blocks_unauthorized_role(auth_env):
    auth = auth_env
    viewer_user = {"role": "viewer"}

    with pytest.raises(HTTPException) as exc:
        auth.require_roles(viewer_user, auth.REPORT_WRITE_ROLES)

    assert exc.value.status_code == 403


def test_create_user_invite_rejects_invalid_role(auth_env):
    auth = auth_env
    admin = auth.get_user_claims(auth.DEFAULT_ADMIN_EMAIL)
    assert admin is not None

    with pytest.raises(HTTPException) as exc:
        auth.create_user_invite(actor=admin, email="bad.role@complyai.io", role="superadmin")

    assert exc.value.status_code == 400
