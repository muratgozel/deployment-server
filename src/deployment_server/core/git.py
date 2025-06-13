import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse


def make_git_url_privileged(git_url: str, token: str = None, user: str = None) -> str:
    parsed_url = urlparse(git_url)
    netloc_privileged = (
        f"{user + ":" if user else ""}{token + "@" if token else ""}{parsed_url.netloc}"
    )
    return urlunparse(
        (parsed_url.scheme, netloc_privileged, parsed_url.path, "", "", "")
    )


def parse_repo_url(repo_url: str):
    """
    Extracts vendor, owner and repository name from a given repository url.
    The format of the url can either be http or ssh.
    The returned owner includes all the paths up to repository name.
    In GitHub, it is org but in Gitlab, it may contain group/subgroup.

    :param repo_url: git repository url
    :return: (vendor, owner, name)
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


def extract_version_from_ref(ref: str) -> str:
    """
    Extracts version string from git reference.
    refs/tags/0.1.2 -> 0.1.2
    refs/tags/v0.1.2 -> 0.1.2

    :param ref: git reference. "refs/tags/0.1.2" for example.
    :return: version string.
    """
    pattern = r"^refs/tags/v?(.+)$"
    matches = re.match(pattern, ref)
    if matches:
        return matches.group(1)

    raise ValueError("Invalid git ref.")
