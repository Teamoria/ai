"""Read-only queries against the Laravel platform database."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class LaravelUserContext:
    id: str
    role: str
    company_id: str | None = None


class LaravelRepository:
    """Small read-only repository for platform data used by the RAG agent."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def visible_project_ids(self, user: LaravelUserContext, project_id: str | None = None) -> list[str]:
        params: dict[str, Any] = {
            "user_id": user.id,
            "company_id": user.company_id,
            "project_id": project_id,
        }
        project_filter = "and p.id = :project_id" if project_id else ""

        if user.role == "admin":
            rows = self.session.execute(
                text(
                    f"""
                    select p.id
                    from projects p
                    where p.deleted_at is null
                    {project_filter}
                    order by p.updated_at desc
                    limit 100
                    """
                ),
                params,
            )
            return [str(row.id) for row in rows]

        if not user.company_id:
            return []

        membership_filter = ""
        if user.role != "company_owner":
            membership_filter = """
                and exists (
                    select 1
                    from project_user pu
                    where pu.project_id = p.id
                      and pu.user_id = :user_id
                )
            """

        rows = self.session.execute(
            text(
                f"""
                select p.id
                from projects p
                where p.deleted_at is null
                  and p.company_id = :company_id
                  {project_filter}
                  {membership_filter}
                order by p.updated_at desc
                limit 100
                """
            ),
            params,
        )
        return [str(row.id) for row in rows]

    def visible_tasks(
        self,
        user: LaravelUserContext,
        project_ids: list[str],
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        if not project_ids:
            return []

        member_task_filter = ""
        if user.role not in {"admin", "company_owner"}:
            member_task_filter = """
                  and (
                    exists (
                        select 1
                        from task_user tu
                        where tu.task_id = t.id
                          and tu.user_id = :user_id
                    )
                    or exists (
                        select 1
                        from project_user pu
                        where pu.project_id = t.project_id
                          and pu.user_id = :user_id
                          and pu.role = 'manager'
                    )
                  )
            """

        rows = self.session.execute(
            text(
                f"""
                select
                    t.id,
                    t.project_id,
                    t.title,
                    t.description,
                    t.status,
                    t.priority,
                    t.due_date,
                    t.updated_at,
                    p.name as project_name
                from tasks t
                join projects p on p.id = t.project_id
                where t.deleted_at is null
                  and t.project_id in :project_ids
                  {member_task_filter}
                order by t.updated_at desc
                limit :limit
                """
            ).bindparams(bindparam("project_ids", expanding=True)),
            {"project_ids": project_ids, "limit": limit, "user_id": user.id},
        )
        return [dict(row._mapping) for row in rows]

    def visible_uploads(
        self,
        user: LaravelUserContext,
        project_ids: list[str],
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "user_id": user.id,
            "company_id": user.company_id,
            "limit": limit,
        }

        if user.role == "admin":
            where = "u.project_id in :project_ids" if project_ids else "1 = 1"
        elif not user.company_id:
            return []
        elif user.role == "company_owner":
            where = "u.company_id = :company_id"
        else:
            manager_project_clause = """
                or (
                    u.scope = 'project'
                    and exists (
                        select 1
                        from project_user pu
                        where pu.project_id = u.project_id
                          and pu.user_id = :user_id
                          and pu.role = 'manager'
                    )
                )
            """
            task_clause = """
                or (
                    u.scope = 'task'
                    and (
                        exists (
                            select 1
                            from task_user tu
                            where tu.task_id = u.task_id
                              and tu.user_id = :user_id
                        )
                        or exists (
                            select 1
                            from project_user pu
                            where pu.project_id = u.project_id
                              and pu.user_id = :user_id
                              and pu.role = 'manager'
                        )
                    )
                )
            """
            where = f"""
                u.company_id = :company_id
                and (
                    u.user_id = :user_id
                    or exists (
                        select 1
                        from upload_permissions up
                        where up.upload_id = u.id
                          and up.user_id = :user_id
                    )
                    {manager_project_clause}
                    {task_clause}
                )
            """

        query = text(
            f"""
            select
                u.id,
                u.company_id,
                u.project_id,
                u.task_id,
                u.user_id,
                u.scope,
                u.visibility,
                u.file_name,
                u.file_type,
                u.category,
                u.status,
                u.upload_date,
                u.updated_at
            from uploads u
            where {where}
            order by coalesce(u.upload_date, u.updated_at) desc
            limit :limit
            """
        )

        if project_ids and user.role == "admin":
            query = query.bindparams(bindparam("project_ids", expanding=True))
            params["project_ids"] = project_ids

        rows = self.session.execute(query, params)
        return [dict(row._mapping) for row in rows]

    def visible_meeting_summaries(
        self,
        upload_ids: list[str],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not upload_ids:
            return []

        rows = self.session.execute(
            text(
                """
                select
                    ms.id,
                    ms.upload_id,
                    ms.summary,
                    ms.transcript,
                    ms.updated_at,
                    u.file_name
                from meeting_summaries ms
                join uploads u on u.id = ms.upload_id
                where ms.upload_id in :upload_ids
                order by ms.updated_at desc
                limit :limit
                """
            ).bindparams(bindparam("upload_ids", expanding=True)),
            {"upload_ids": upload_ids, "limit": limit},
        )
        return [dict(row._mapping) for row in rows]

    def visible_knowledge_chunks(
        self,
        project_ids: list[str],
        upload_ids: list[str],
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not project_ids and not upload_ids:
            return []

        clauses: list[str] = []
        params: dict[str, Any] = {"limit": limit}
        if project_ids:
            clauses.append("kc.project_id in :project_ids")
            params["project_ids"] = project_ids
        if upload_ids:
            clauses.append("kc.upload_id in :upload_ids")
            params["upload_ids"] = upload_ids

        query = text(
            f"""
            select
                kc.id,
                kc.project_id,
                kc.upload_id,
                kc.content,
                kc.metadata,
                kc.updated_at
            from knowledge_chunks kc
            where {" or ".join(clauses)}
            order by kc.updated_at desc
            limit :limit
            """
        )
        if project_ids:
            query = query.bindparams(bindparam("project_ids", expanding=True))
        if upload_ids:
            query = query.bindparams(bindparam("upload_ids", expanding=True))

        rows = self.session.execute(query, params)
        return [dict(row._mapping) for row in rows]

    def ai_chat_knowledge_chunks(
        self,
        user_id: str,
        company_id: str,
        project_id: str | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        project_filter = ""
        params: dict[str, Any] = {"user_id": user_id, "company_id": company_id, "limit": limit}
        if project_id is not None:
            project_filter = """
                  and (
                    cast(u.project_id as varchar) = :project_id
                    or cast(kc.project_id as varchar) = :project_id
                  )
            """
            params["project_id"] = project_id

        rows = self.session.execute(
            text(
                f"""
                select
                    kc.id,
                    kc.project_id,
                    kc.upload_id,
                    kc.content,
                    kc.metadata,
                    kc.updated_at,
                    u.file_name,
                    u.upload_date,
                    u.updated_at as upload_updated_at,
                    u.company_id,
                    u.project_id as upload_project_id
                from knowledge_chunks kc
                join uploads u on u.id = kc.upload_id
                where kc.content is not null
                  and kc.content <> ''
                  {project_filter}
                  and (
                    cast(u.user_id as varchar) = :user_id
                    or exists (
                        select 1
                        from upload_permissions up
                        where up.upload_id = u.id
                          and cast(up.user_id as varchar) = :user_id
                    )
                    or cast(u.company_id as varchar) = :company_id
                  )
                order by coalesce(u.upload_date, u.updated_at, kc.updated_at) desc, kc.id desc
                limit :limit
                """
            ),
            params,
        )
        return [dict(row._mapping) for row in rows]

    def ai_chat_visible_uploads(
        self,
        user_id: str,
        company_id: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        project_filter = ""
        params: dict[str, Any] = {"user_id": user_id, "company_id": company_id, "limit": limit}
        if project_id is not None:
            project_filter = "and cast(u.project_id as varchar) = :project_id"
            params["project_id"] = project_id

        rows = self.session.execute(
            text(
                f"""
                select
                    u.id,
                    u.company_id,
                    u.project_id,
                    u.task_id,
                    u.user_id,
                    u.scope,
                    u.visibility,
                    u.file_name,
                    u.file_type,
                    u.category,
                    u.status,
                    u.upload_date,
                    u.updated_at,
                    case
                        when cast(u.user_id as varchar) = :user_id then 'owned'
                        when exists (
                            select 1
                            from upload_permissions up
                            where up.upload_id = u.id
                              and cast(up.user_id as varchar) = :user_id
                        ) then 'shared'
                        when cast(u.company_id as varchar) = :company_id then 'company'
                        else 'visible'
                    end as access_reason
                from uploads u
                where (
                    cast(u.user_id as varchar) = :user_id
                    or exists (
                        select 1
                        from upload_permissions up
                        where up.upload_id = u.id
                          and cast(up.user_id as varchar) = :user_id
                    )
                    or cast(u.company_id as varchar) = :company_id
                )
                {project_filter}
                order by coalesce(u.upload_date, u.updated_at) desc, u.id desc
                limit :limit
                """
            ),
            params,
        )
        return [dict(row._mapping) for row in rows]

    def ai_chat_identity_exists(self, user_id: str, company_id: str) -> dict[str, bool]:
        user_exists = self.session.execute(
            text("select 1 from users where cast(id as varchar) = :user_id limit 1"),
            {"user_id": user_id},
        ).scalar() is not None
        company_exists = self.session.execute(
            text("select 1 from companies where cast(id as varchar) = :company_id limit 1"),
            {"company_id": company_id},
        ).scalar() is not None
        user_in_company = self.session.execute(
            text(
                """
                select 1
                from users
                where cast(id as varchar) = :user_id
                  and cast(company_id as varchar) = :company_id
                limit 1
                """
            ),
            {"user_id": user_id, "company_id": company_id},
        ).scalar() is not None

        return {
            "user_exists": user_exists,
            "company_exists": company_exists,
            "user_in_company": user_in_company,
        }

    def ai_chat_visible_projects(
        self,
        user_id: str,
        company_id: str,
        project_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        project_filter = ""
        params: dict[str, Any] = {"user_id": user_id, "company_id": company_id, "limit": limit}
        if project_id is not None:
            project_filter = "and cast(p.id as varchar) = :project_id"
            params["project_id"] = project_id

        rows = self.session.execute(
            text(
                f"""
                select
                    p.id,
                    p.company_id,
                    p.name,
                    p.description,
                    p.status,
                    p.progress,
                    p.start_date,
                    p.end_date,
                    p.updated_at,
                    case
                        when exists (
                            select 1
                            from project_user pu
                            where pu.project_id = p.id
                              and cast(pu.user_id as varchar) = :user_id
                        ) then 'member'
                        when cast(p.company_id as varchar) = :company_id then 'company'
                        else 'visible'
                    end as access_reason
                from projects p
                where p.deleted_at is null
                  {project_filter}
                  and (
                    cast(p.company_id as varchar) = :company_id
                    or exists (
                        select 1
                        from project_user pu
                        where pu.project_id = p.id
                          and cast(pu.user_id as varchar) = :user_id
                    )
                  )
                order by p.updated_at desc, p.id desc
                limit :limit
                """
            ),
            params,
        )
        return [dict(row._mapping) for row in rows]

    def ai_chat_visible_tasks(
        self,
        user_id: str,
        company_id: str,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        project_filter = ""
        params: dict[str, Any] = {"user_id": user_id, "company_id": company_id, "limit": limit}
        if project_id is not None:
            project_filter = "and cast(t.project_id as varchar) = :project_id"
            params["project_id"] = project_id

        rows = self.session.execute(
            text(
                f"""
                select
                    t.id,
                    t.project_id,
                    t.title,
                    t.description,
                    t.status,
                    t.priority,
                    t.due_date,
                    t.updated_at,
                    p.name as project_name,
                    case
                        when exists (
                            select 1
                            from task_user tu
                            where tu.task_id = t.id
                              and cast(tu.user_id as varchar) = :user_id
                        ) then 'assigned'
                        when exists (
                            select 1
                            from project_user pu
                            where pu.project_id = t.project_id
                              and cast(pu.user_id as varchar) = :user_id
                        ) then 'project_member'
                        when cast(p.company_id as varchar) = :company_id then 'company'
                        else 'visible'
                    end as access_reason
                from tasks t
                join projects p on p.id = t.project_id
                where t.deleted_at is null
                  {project_filter}
                  and (
                    exists (
                        select 1
                        from task_user tu
                        where tu.task_id = t.id
                          and cast(tu.user_id as varchar) = :user_id
                    )
                    or exists (
                        select 1
                        from project_user pu
                        where pu.project_id = t.project_id
                          and cast(pu.user_id as varchar) = :user_id
                    )
                    or cast(p.company_id as varchar) = :company_id
                  )
                order by coalesce(t.due_date, t.updated_at) asc, t.id desc
                limit :limit
                """
            ),
            params,
        )
        return [dict(row._mapping) for row in rows]
