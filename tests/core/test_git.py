from deployment_server.core import git


def test_git():
    result = git.make_git_url_privileged(
        "git://github.com/coldrune/server.git", "12345"
    )
    assert result == "git://12345@github.com/coldrune/server.git"

    result = git.make_git_url_privileged("https://pypi.gozel.com.tr/simple/", "12345")
    assert result == "https://12345@pypi.gozel.com.tr/simple/"

    result = git.make_git_url_privileged(
        "https://pypi.gozel.com.tr/simple/", "12345", "user"
    )
    assert result == "https://user:12345@pypi.gozel.com.tr/simple/"

    result = git.make_git_url_privileged("https://pypi.gozel.com.tr/simple/")
    assert result == "https://pypi.gozel.com.tr/simple/"
