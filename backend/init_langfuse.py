import asyncio
import os

import httpx
from sqlalchemy import text

from database import AsyncSessionLocal


LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "http://langfuse:3000")
EMAIL = "admin@worknoon.local"
PASSWORD = "worknoon-admin"


async def repair_project_memberships() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO project_memberships
                  (project_id, user_id, org_membership_id, role, created_at, updated_at)
                SELECT p.id, om.user_id, om.id, 'OWNER', now(), now()
                FROM projects p
                JOIN organization_memberships om ON om.org_id = p.org_id
                WHERE NOT EXISTS (
                  SELECT 1
                  FROM project_memberships pm
                  WHERE pm.project_id = p.id AND pm.user_id = om.user_id
                )
                """
            )
        )
        await session.commit()


async def init_langfuse() -> None:
    if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
        try:
            await repair_project_memberships()
        except Exception:
            pass
        return

    async with httpx.AsyncClient(base_url=LANGFUSE_HOST, timeout=10, follow_redirects=True) as client:
        for _ in range(30):
            try:
                health = await client.get("/api/public/health")
                if health.status_code < 500:
                    break
            except httpx.HTTPError:
                pass
            await asyncio.sleep(2)

        try:
            await client.post("/api/auth/signup", json={"email": EMAIL, "password": PASSWORD, "name": "Admin"})
        except httpx.HTTPError:
            pass

        token = None
        try:
            signin = await client.post("/api/auth/signin", json={"email": EMAIL, "password": PASSWORD})
            data = signin.json()
            token = data.get("token") or data.get("accessToken")
        except Exception:
            token = None

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            project = await client.post("/api/projects", json={"name": "worknoon-refund-agent"}, headers=headers)
            project_data = project.json()
            project_id = project_data.get("id") or project_data.get("projectId")
            if project_id:
                keys = await client.post(f"/api/projects/{project_id}/apiKeys", headers=headers)
                key_data = keys.json()
                os.environ["LANGFUSE_PUBLIC_KEY"] = key_data.get("publicKey", "")
                os.environ["LANGFUSE_SECRET_KEY"] = key_data.get("secretKey", "")
                with open("/tmp/langfuse.env", "w") as env_file:
                    env_file.write(f"export LANGFUSE_PUBLIC_KEY='{os.environ['LANGFUSE_PUBLIC_KEY']}'\n")
                    env_file.write(f"export LANGFUSE_SECRET_KEY='{os.environ['LANGFUSE_SECRET_KEY']}'\n")
        except Exception:
            return

    try:
        await repair_project_memberships()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(init_langfuse())
