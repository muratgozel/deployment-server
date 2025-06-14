import os


def test_env():
    assert isinstance(os.environ.get("API_USER"), str)
