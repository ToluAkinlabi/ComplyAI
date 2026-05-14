import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException


@pytest.fixture()
def usage_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "usage_limits_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("AUTO_INIT_DB", "true")
    monkeypatch.setenv("STRICT_MIGRATIONS", "false")

    import database.session as session_module
    import database.models as models_module
    import database.report_store as report_store_module
    import scripts.usage_limits as usage_limits_module

    session_module = importlib.reload(session_module)
    models_module = importlib.reload(models_module)
    models_module.Base.metadata.create_all(bind=session_module.engine)
    report_store_module = importlib.reload(report_store_module)
    usage_limits_module = importlib.reload(usage_limits_module)

    yield report_store_module, usage_limits_module, models_module, session_module

    models_module.Base.metadata.drop_all(bind=session_module.engine)


def test_enforce_monthly_limit_blocks_when_reached(usage_env, monkeypatch: pytest.MonkeyPatch):
    report_store, usage_limits, _, _ = usage_env
    user = {"org_id": 77, "user_id": 770, "email": "member@org77.io"}

    report_store.create_report_record(
        client_name="Client 1",
        document_name="Doc 1",
        report_data={},
        report_file_name="doc-1.pdf",
        json_file_name="doc-1.json",
        file_size=100,
        processing_time_seconds=1,
        user=user,
    )

    monkeypatch.setenv("MONTHLY_REPORT_LIMIT_PER_ORG", "1")

    with pytest.raises(HTTPException) as exc:
        usage_limits.enforce_monthly_report_limit(user)

    assert exc.value.status_code == 429
    assert "quota reached" in exc.value.detail.lower()


def test_enforce_monthly_limit_allows_when_under_limit(usage_env, monkeypatch: pytest.MonkeyPatch):
    report_store, usage_limits, _, _ = usage_env
    user = {"org_id": 88, "user_id": 880, "email": "member@org88.io"}

    report_store.create_report_record(
        client_name="Client 2",
        document_name="Doc 2",
        report_data={},
        report_file_name="doc-2.pdf",
        json_file_name="doc-2.json",
        file_size=100,
        processing_time_seconds=1,
        user=user,
    )

    monkeypatch.setenv("MONTHLY_REPORT_LIMIT_PER_ORG", "5")
    usage_limits.enforce_monthly_report_limit(user)


def test_limit_disabled_or_no_org_is_noop(usage_env, monkeypatch: pytest.MonkeyPatch):
    _, usage_limits, _, _ = usage_env

    monkeypatch.setenv("MONTHLY_REPORT_LIMIT_PER_ORG", "0")
    usage_limits.enforce_monthly_report_limit({"org_id": 1})

    monkeypatch.setenv("MONTHLY_REPORT_LIMIT_PER_ORG", "3")
    usage_limits.enforce_monthly_report_limit(None)
