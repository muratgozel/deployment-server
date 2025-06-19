from deployment_server.packages.utils.extractors import (
    information_from_git_repo_url,
    tag_from_git_ref,
)


def test_extract_info_from_repo_url():
    samples = (
        "https://github.com/the-org/the-name.git",
        "git://github.com/the-org/the-name.git",
        "git@github.com:/the-org/the-name.git",
    )
    for sample in samples:
        assert information_from_git_repo_url(sample) == (
            "github.com",
            "the-org",
            "the-name",
        )


def test_extract_version_from_ref():
    samples = (
        ("refs/tags/0.1.2", "0.1.2"),
        ("refs/tags/v0.1.2", "v0.1.2"),
        ("refs/tags/v0.1.2-dev1", "v0.1.2-dev1"),
    )
    for sample in samples:
        assert tag_from_git_ref(sample[0]) == sample[1]
