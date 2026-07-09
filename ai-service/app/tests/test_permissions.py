"""Permission scope tests."""

from types import SimpleNamespace

from app.repositories.laravel_repository import LaravelRepository, LaravelUserContext


class CaptureSession:
    def __init__(self) -> None:
        self.statement = ""
        self.params = {}

    def execute(self, statement, params=None):
        self.statement = str(statement)
        self.params = params or {}
        return []


class MySqlCaptureSession(CaptureSession):
    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="mysql"))


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


def test_ai_chat_chunks_are_limited_to_owner_permissions_or_company() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.ai_chat_knowledge_chunks(user_id="15", company_id="2", project_id="9")

    assert "from knowledge_chunks kc" in session.statement
    assert "join uploads u on u.id = kc.upload_id" in session.statement
    assert "cast(u.user_id as varchar) = :user_id" in session.statement
    assert "cast(u.project_id as varchar) = :project_id" in session.statement
    assert "cast(kc.project_id as varchar) = :project_id" in session.statement
    assert "from upload_permissions up" in session.statement
    assert "cast(up.user_id as varchar) = :user_id" in session.statement
    assert "cast(u.company_id as varchar) = :company_id" in session.statement
    assert "order by coalesce(u.upload_date, u.updated_at, kc.updated_at) desc" in session.statement
    assert session.params["user_id"] == "15"
    assert session.params["company_id"] == "2"
    assert session.params["project_id"] == "9"


def test_ai_chat_chunks_do_not_bind_project_id_when_missing() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.ai_chat_knowledge_chunks(user_id="15", company_id="2")

    assert "cast(u.project_id as varchar) = :project_id" not in session.statement
    assert "cast(kc.project_id as varchar) = :project_id" not in session.statement
    assert "project_id" not in session.params
    assert session.params["user_id"] == "15"
    assert session.params["company_id"] == "2"


def test_ai_chat_visible_uploads_reads_latest_visible_files() -> None:
    session = CaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.ai_chat_visible_uploads(user_id="15", company_id="2", project_id="9")

    assert "from uploads u" in session.statement
    assert "cast(u.user_id as varchar) = :user_id" in session.statement
    assert "from upload_permissions up" in session.statement
    assert "cast(up.user_id as varchar) = :user_id" in session.statement
    assert "cast(u.company_id as varchar) = :company_id" in session.statement
    assert "cast(u.project_id as varchar) = :project_id" in session.statement
    assert "case" in session.statement
    assert "owned" in session.statement
    assert "shared" in session.statement
    assert "order by coalesce(u.upload_date, u.updated_at) desc" in session.statement
    assert session.params["user_id"] == "15"
    assert session.params["company_id"] == "2"
    assert session.params["project_id"] == "9"


def test_ai_chat_queries_use_mysql_compatible_casts_for_mysql() -> None:
    session = MySqlCaptureSession()
    repository = LaravelRepository(session)  # type: ignore[arg-type]

    repository.ai_chat_visible_uploads(user_id="15", company_id="2", project_id="9")

    assert "cast(u.user_id as char) = :user_id" in session.statement
    assert "cast(u.project_id as char) = :project_id" in session.statement
    assert "cast(u.user_id as varchar) = :user_id" not in session.statement
