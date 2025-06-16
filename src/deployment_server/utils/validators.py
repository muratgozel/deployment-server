import re
from urllib.parse import urlparse


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


def validate_url_pydantic(url: str):
    if validate_url(url)[0] is False:
        raise ValueError("invalid url")
    return url.lower()


def validate_url(url: str, required_attrs: str = ("scheme", "netloc", "path"), scheme_whitelist: tuple[str] = ("https", "http", "git")):
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


def validate_pip_package_name_pydantic(name: str):
    if validate_pip_package_name(name) is True:
        return normalize_pip_package_name(name)
    raise ValueError("invalid package name")


def validate_pip_package_name(name: str):
    matches = re.match(f"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", name, re.IGNORECASE)
    return False if not matches else True


def normalize_pip_package_name(name: str):
    return re.sub(r"[-_.]+", "-", name).lower()
