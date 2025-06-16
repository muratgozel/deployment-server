from urllib.parse import urlparse, urlunparse


def add_auth(url: str, password: str = None, user: str = None):
    parsed_url = urlparse(url)
    netloc_with_auth = (
        (user + ":" if user else "")
        + (password + "@" if password else "")
        + parsed_url.netloc
    )
    return urlunparse(
        (parsed_url.scheme, netloc_with_auth, parsed_url.path, "", "", "")
    )
