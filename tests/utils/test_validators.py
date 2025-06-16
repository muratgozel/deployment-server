from deployment_server.utils import validators


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
        "git://github.com/",
    )
    invalid_samples = (None, "", "git://git://github.com/coldrune/server.git")

    for sample in valid_samples:
        assert validators.validate_url(sample)[0] == True

    for sample in invalid_samples:
        print(sample)
        assert validators.validate_url(sample)[0] == False
