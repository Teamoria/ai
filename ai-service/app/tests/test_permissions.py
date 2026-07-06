"""Permission scope tests."""

from app.repositories.laravel_repository import LaravelRepository, LaravelUserContext


class CaptureSession:
    def __init__(self) -> None:
        self.statement = ""
        self.params = {}

    def execute(self, statement, params=None):
        self.statement = str(statement)
        self.params = params or {}
        return []


def test_member_tasks_are_limited_to_assigned_tasks_or_managed_projects() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.visible_tasks(
        LaravelUserContext(id="user-1", role="member", company_id="company-1"),
        ["project-1"],
    )

    assert "from task_user tu" in session.statement
    assert "tu.user_id = :user_id" in session.statement
    assert "from project_user pu" in session.statement
    assert session.params["user_id"] == "user-1"


def test_admin_tasks_are_not_limited_by_assignment() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.visible_tasks(
        LaravelUserContext(id="admin-1", role="admin", company_id=None),
        ["project-1"],
    )

    assert "from task_user tu" not in session.statement
    assert "from project_user pu" not in session.statement


def test_member_uploads_do_not_include_all_company_member_files() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.visible_uploads(
        LaravelUserContext(id="user-1", role="member", company_id="company-1"),
        ["project-1"],
    )

    assert "u.user_id = :user_id" in session.statement
    assert "from upload_permissions up" in session.statement
    assert "from task_user tu" in session.statement
    assert "u.visibility = 'members'" not in session.statement
    assert "u.scope = 'company'" not in session.statement
    assert session.params["user_id"] == "user-1"


def test_company_owner_uploads_are_limited_to_company() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.visible_uploads(
        LaravelUserContext(id="owner-1", role="company_owner", company_id="company-1"),
        ["project-1"],
    )

    assert "u.company_id = :company_id" in session.statement
    assert "u.visibility = 'members'" not in session.statement
    assert session.params["company_id"] == "company-1"
