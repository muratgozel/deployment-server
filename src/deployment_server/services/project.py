from slugify import slugify
from deployment_server.repositories.project import ProjectRepository
from deployment_server.models import Project, SystemdUnit


class ProjectService:
    def __init__(self, project_repo: ProjectRepository):
        self.project_repo: ProjectRepository = project_repo

    async def get_all(self):
        return await self.project_repo.get_all()

    async def get_by_code(self, code: str):
        return await self.project_repo.get_one_by("code", code)

    def get_by_code_sync(self, code: str):
        return self.project_repo.get_one_by_sync("code", code)

    async def get_by_rid(self, rid: str):
        return await self.project_repo.get_one_by("rid", rid)

    async def get_by_git_url(self, git_url: str):
        return await self.project_repo.get_one_by("git_url", git_url)

    def validate_code(self, code: str) -> str | bool:
        validated_code = slugify(code)
        if len(validated_code) == 0:
            return False
        return validated_code

    async def create(
        self,
        name: str,
        code: str,
        git_url: str = None,
        pip_package_name: str = None,
        pip_index_url: str = None,
        pip_index_user: str = None,
        pip_index_auth: str = None,
        daemons: list[SystemdUnit] = None,
    ):
        project = Project(
            rid=Project.generate_rid(),
            name=name,
            code=code,
            git_url=git_url,
            pip_package_name=pip_package_name,
            pip_index_url=pip_index_url,
            pip_index_user=pip_index_user,
            pip_index_auth=pip_index_auth,
        )
        return await self.project_repo.add(project=project, daemons=daemons)

    async def remove_by_rid(self, rid: str):
        return await self.project_repo.remove_by_rid(rid=rid)
