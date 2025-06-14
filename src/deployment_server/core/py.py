import re


def validate_pip_package_name_pydantic(name: str):
    if validate_pip_package_name(name) is True:
        return normalize_pip_package_name(name)
    raise ValueError("invalid package name")


def validate_pip_package_name(name: str):
    matches = re.match(f"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", name, re.IGNORECASE)
    return False if not matches else True


def normalize_pip_package_name(name: str):
    return re.sub(r"[-_.]+", "-", name).lower()
