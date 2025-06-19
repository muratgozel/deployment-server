from deployment_server.packages.utils.modifiers import add_auth_to_url


def test_add_auth():
    samples = (
        (
            "git://github.com/coldrune/server.git",
            "12345",
            None,
            "git://12345@github.com/coldrune/server.git",
        ),
        (
            "https://pypi.gozel.com.tr/simple/",
            "12345",
            None,
            "https://12345@pypi.gozel.com.tr/simple/",
        ),
        (
            "https://pypi.gozel.com.tr/simple/",
            "12345",
            "user",
            "https://user:12345@pypi.gozel.com.tr/simple/",
        ),
        (
            "https://pypi.gozel.com.tr/simple/",
            None,
            None,
            "https://pypi.gozel.com.tr/simple/",
        ),
    )

    for sample in samples:
        assert (
            add_auth_to_url(
                sample[0], password=sample[1] or None, user=sample[2] or None
            )
            == sample[3]
        )
