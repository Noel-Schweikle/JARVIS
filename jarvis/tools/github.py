from github import Github, GithubException
import config

_github = None


def _get_github() -> Github:
    global _github
    if _github is None:
        _github = Github(config.GITHUB_TOKEN)
    return _github


def read_file(path: str, repo: str = None) -> str:
    repo_name = repo or config.GITHUB_REPO
    if not repo_name:
        return "Fehler: Kein GitHub Repository konfiguriert (GITHUB_REPO in .env setzen)"

    g = _get_github()
    try:
        r = g.get_repo(repo_name)
        content = r.get_contents(path)
        if isinstance(content, list):
            return "\n".join(c.path for c in content)
        return content.decoded_content.decode("utf-8")
    except GithubException as e:
        return f"GitHub Fehler: {e.data.get('message', str(e))}"


def write_file(path: str, content: str, message: str, repo: str = None) -> str:
    repo_name = repo or config.GITHUB_REPO
    if not repo_name:
        return "Fehler: Kein GitHub Repository konfiguriert"

    g = _get_github()
    try:
        r = g.get_repo(repo_name)
        try:
            existing = r.get_contents(path)
            r.update_file(path, message, content, existing.sha)
            return f"Datei aktualisiert: {path}"
        except GithubException:
            r.create_file(path, message, content)
            return f"Datei erstellt: {path}"
    except GithubException as e:
        return f"GitHub Fehler: {e.data.get('message', str(e))}"


def list_repos() -> str:
    if not config.GITHUB_TOKEN:
        return "Fehler: Kein GitHub Token konfiguriert"

    g = _get_github()
    try:
        user = g.get_user()
        repos = user.get_repos(sort="updated")
        lines = []
        for r in repos:
            visibility = "privat" if r.private else "öffentlich"
            lines.append(f"{r.full_name}  [{visibility}]  {r.description or ''}")
        return "\n".join(lines) if lines else "Keine Repositories gefunden."
    except GithubException as e:
        return f"GitHub Fehler: {e.data.get('message', str(e))}"


def list_files(path: str = "", repo: str = None) -> str:
    repo_name = repo or config.GITHUB_REPO
    if not repo_name:
        return "Fehler: Kein GitHub Repository konfiguriert"

    g = _get_github()
    try:
        r = g.get_repo(repo_name)
        contents = r.get_contents(path)
        if not isinstance(contents, list):
            contents = [contents]
        return "\n".join(f"[{c.type}] {c.path}" for c in contents)
    except GithubException as e:
        return f"GitHub Fehler: {e.data.get('message', str(e))}"
