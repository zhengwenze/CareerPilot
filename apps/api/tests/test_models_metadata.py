from app.db.base import Base


def test_metadata_includes_job_and_match_tables() -> None:
    assert "job_descriptions" in Base.metadata.tables
    assert "job_parse_jobs" in Base.metadata.tables
    assert "job_readiness_events" in Base.metadata.tables
    assert "match_reports" in Base.metadata.tables
    assert "resume_optimization_sessions" in Base.metadata.tables


def test_match_reports_foreign_keys_reference_expected_tables() -> None:
    match_reports = Base.metadata.tables["match_reports"]
    foreign_key_targets = {
        foreign_key.target_fullname
        for column in match_reports.columns
        for foreign_key in column.foreign_keys
    }

    assert "users.id" in foreign_key_targets
    assert "resumes.id" in foreign_key_targets
    assert "job_descriptions.id" in foreign_key_targets
