import importlib
from pathlib import Path

import pytest


@pytest.fixture()
def report_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "complyai_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("AUTO_INIT_DB", "true")
    monkeypatch.setenv("STRICT_MIGRATIONS", "false")

    import database.session as session_module
    import database.models as models_module
    import database.report_store as report_store_module

    session_module = importlib.reload(session_module)
    models_module = importlib.reload(models_module)
    models_module.Base.metadata.create_all(bind=session_module.engine)
    report_store_module = importlib.reload(report_store_module)

    yield report_store_module, session_module, models_module

    models_module.Base.metadata.drop_all(bind=session_module.engine)


def test_org_scoped_list_reports(report_env):
    report_store, _, _ = report_env

    user_org_1 = {"org_id": 1, "user_id": 11, "email": "a@org1.io"}
    user_org_2 = {"org_id": 2, "user_id": 22, "email": "b@org2.io"}

    report_store.create_report_record(
        client_name="Client A",
        document_name="Policy A",
        report_data={"ok": True},
        report_file_name="org1_report.pdf",
        json_file_name="org1_report.json",
        file_size=100,
        processing_time_seconds=1,
        user=user_org_1,
    )
    report_store.create_report_record(
        client_name="Client B",
        document_name="Policy B",
        report_data={"ok": True},
        report_file_name="org2_report.pdf",
        json_file_name="org2_report.json",
        file_size=100,
        processing_time_seconds=1,
        user=user_org_2,
    )

    org1_records = report_store.list_report_records_for_user(user_org_1, include_type="pdf")
    org2_records = report_store.list_report_records_for_user(user_org_2, include_type="pdf")

    assert len(org1_records) == 1
    assert org1_records[0].report_file_name == "org1_report.pdf"
    assert len(org2_records) == 1
    assert org2_records[0].report_file_name == "org2_report.pdf"


def test_cross_org_record_lookup_is_blocked(report_env):
    report_store, _, _ = report_env

    owner = {"org_id": 44, "user_id": 100, "email": "owner@org44.io"}
    outsider = {"org_id": 45, "user_id": 200, "email": "outsider@org45.io"}

    report_store.create_report_record(
        client_name="Sensitive Co",
        document_name="Sensitive Policy",
        report_data={"classification": "secret"},
        report_file_name="sensitive.pdf",
        json_file_name="sensitive.json",
        file_size=200,
        processing_time_seconds=2,
        user=owner,
    )

    owned = report_store.get_report_record_for_user(owner, "sensitive.pdf")
    blocked = report_store.get_report_record_for_user(outsider, "sensitive.pdf")

    assert owned is not None
    assert blocked is None


def test_history_filters_search_status_and_pagination(report_env):
    report_store, session_module, models_module = report_env

    user = {"org_id": 9, "user_id": 9, "email": "member@org9.io"}

    report_store.create_report_record(
        client_name="Alpha",
        document_name="Alpha Policy",
        report_data={},
        report_file_name="alpha.pdf",
        json_file_name="alpha.json",
        file_size=300,
        processing_time_seconds=3,
        user=user,
    )
    report_store.create_report_record(
        client_name="Beta",
        document_name="Beta Policy",
        report_data={},
        report_file_name="beta.pdf",
        json_file_name="beta.json",
        file_size=400,
        processing_time_seconds=4,
        user=user,
    )
    report_store.create_report_record(
        client_name="Gamma",
        document_name="Gamma Policy",
        report_data={},
        report_file_name="gamma.pdf",
        json_file_name="gamma.json",
        file_size=500,
        processing_time_seconds=5,
        user=user,
    )

    with session_module.SessionLocal() as db:
        beta = db.query(models_module.ComplianceReport).filter_by(report_file_name="beta.pdf").one()
        beta.status = "failed"
        db.commit()

    failed_history = report_store.list_report_history_for_user(user, status="failed")
    assert failed_history["pagination"]["total"] == 1
    assert failed_history["items"][0]["report_file_name"] == "beta.pdf"

    search_history = report_store.list_report_history_for_user(user, search="gamma")
    assert search_history["pagination"]["total"] == 1
    assert search_history["items"][0]["report_file_name"] == "gamma.pdf"

    paged_history = report_store.list_report_history_for_user(user, limit=1, offset=0)
    assert paged_history["pagination"]["limit"] == 1
    assert paged_history["pagination"]["total"] == 3
    assert paged_history["pagination"]["has_more"] is True
    assert len(paged_history["items"]) == 1
