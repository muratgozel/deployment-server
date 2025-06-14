import re
from urllib.parse import urlparse, urlunparse

ul = "\u00a1-\uffff"
ipv4_re = (
    r"(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)"
    r"(?:\.(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)){3}"
)
ipv6_re = r"\[[0-9a-f:.]+\]"
hostname_re = r"[a-z" + ul + r"0-9](?:[a-z" + ul + r"0-9-]{0,61}[a-z" + ul + r"0-9])?"
domain_re = r"(?:\.(?!-)[a-z" + ul + r"0-9-]{1,63}(?<!-))*"
tld_no_fqdn_re = (
    r"\."  # dot
    r"(?!-)"  # can't start with a dash
    r"(?:[a-z" + ul + "-]{2,63}"  # domain label
    r"|xn--[a-z0-9]{1,59})"  # or punycode label
    r"(?<!-)"  # can't end with a dash
)
tld_re = tld_no_fqdn_re + r"\.?"
host_re = "(" + hostname_re + domain_re + tld_re + "|localhost)"


def validate_pydantic(url: str):
    if validate(url)[0] is False:
        raise ValueError("invalid url")
    return url.lower()


def validate(url: str, required_attrs: str = ("scheme", "netloc", "path"), scheme_whitelist: tuple[str] = ("https", "http", "git")):
    try:
        tokens = urlparse(url)
    except Exception as ex:
        return False, f"urlparse error: {str(ex)}"

    all_exist = all(getattr(tokens, qualifying_attr) for qualifying_attr in required_attrs)
    if not all_exist:
        return False, "missing required tokens"

    if "scheme" in required_attrs and tokens.scheme not in scheme_whitelist:
        return False, "unsupported scheme"

    if "netloc" in required_attrs:
        if re.fullmatch(r"(?:" + ipv4_re + "|" + ipv6_re + "|" + host_re + ")", tokens.netloc) is None:
            return False, "invalid netloc"

    if "path" in required_attrs:
        if len(tokens.path) == 0 or tokens.path.startswith("/") is False:
            return False, "either path doesn't start with '/' or it's empty"
        if re.fullmatch(r"(?:[/?#][^\s]*)?", tokens.path) is None:
            return False, "invalid path"

    return True, ""


def add_auth(url: str, password: str = None, user: str = None):
    parsed_url = urlparse(url)
    netloc_with_auth = (
        (user + ":" if user else "") +
        (password + "@" if password else "") +
        parsed_url.netloc
    )
    return urlunparse(
        (parsed_url.scheme, netloc_with_auth, parsed_url.path, "", "", "")
    )
