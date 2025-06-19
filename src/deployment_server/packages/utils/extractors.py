import re
from pathlib import Path
from urllib.parse import urlparse


def information_from_git_repo_url(repo_url: str):
    """
    Extracts vendor, owner and repository name from a given repository url.

    :param repo_url: A git repository url. Both http and ssh formats are supported.
    :return: A tuple containing (vendor, owner, name). (gitlab.com, group/subgroup, name) for example.
    """
    repo_url = repo_url.strip()

    if repo_url.startswith("http") or repo_url.startswith("git://"):
        parsed_url = urlparse(repo_url)
        vendor = parsed_url.hostname
        pass
    elif repo_url.startswith("git"):
        vendor = repo_url[repo_url.find("@") + 1 : repo_url.find(":")]
        parsed_url = urlparse(f"http://localhost/{repo_url[repo_url.find(":")+1:]}")
    else:
        raise ValueError(f"Invalid repo url: {repo_url}")

    p = parsed_url.path
    if p.startswith("/"):
        p = p.lstrip("/")
    last_slash_ind = p.rfind("/")
    owner = p[:last_slash_ind]
    name = Path(p[last_slash_ind + 1 :]).stem

    return vendor, owner, name


def tag_from_git_ref(ref: str) -> str:
    """
    Extracts version string from git reference.
    refs/tags/0.1.2 -> 0.1.2
    refs/tags/v0.1.2 -> v0.1.2

    :param ref: git reference. "refs/tags/0.1.2" for example.
    :return: version string.
    """
    pattern = r"^refs/tags/(.+)$"
    matches = re.match(pattern, ref)
    if matches:
        return matches.group(1)

    raise ValueError("Invalid git ref.")
