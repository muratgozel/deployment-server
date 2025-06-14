from deployment_server.core import urlextra


def test_validate():
    valid_samples = (
        "git://github.com/coldrune/server.git",
        "http://localhost/coldrune/server.git",
        "http://127.0.0.1/coldrune/server.git",
        "http://154.3.12.78/coldrune/server.git",
        "http://[2001:0db8:85a3:0000:0000:8a2e:0370:7334]/coldrune/server.git",
        "http://[::]/coldrune/server.git",
        "http://[2001:db8::]/coldrune/server.git",
        "https://pypi.gozel.com.tr/",
        "git://github.com/"
    )
    invalid_samples = (
        None,
        "",
        "git://git://github.com/coldrune/server.git"
    )

    for sample in valid_samples:
        assert urlextra.validate(sample)[0] == True

    for sample in invalid_samples:
        print(sample)
        assert urlextra.validate(sample)[0] == False


def test_add_auth():
    samples = (
        ("git://github.com/coldrune/server.git", "12345", None, "git://12345@github.com/coldrune/server.git"),
        ("https://pypi.gozel.com.tr/simple/", "12345", None, "https://12345@pypi.gozel.com.tr/simple/"),
        ("https://pypi.gozel.com.tr/simple/", "12345", "user", "https://user:12345@pypi.gozel.com.tr/simple/"),
        ("https://pypi.gozel.com.tr/simple/", None, None, "https://pypi.gozel.com.tr/simple/")
    )

    for sample in samples:
        assert urlextra.add_auth(sample[0], password=sample[1] or None, user=sample[2] or None) == sample[3]
