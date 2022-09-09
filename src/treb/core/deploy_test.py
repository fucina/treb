from pathlib import Path

from testfixtures import ShouldRaise, compare, generator

from treb.core.deploy import DeployFile, Vars, discover_deploy_files

DUMMY_CONTENT = """wait(
    name="sleep",
    duration=60,
)
"""


def _create_dummy_deploy_file(path: Path):
    with open(path, "w") as fp:
        fp.write(DUMMY_CONTENT)


def test_discover_deploy_files__no_deploy_files_returns_empty_iterator(tmp_path_factory):
    res = discover_deploy_files(tmp_path_factory.getbasetemp())

    compare(generator(), res)


def test_discover_deploy_files__find_file_in_root_directory(tmp_path_factory):
    path = tmp_path_factory.getbasetemp() / "DEPLOY"
    _create_dummy_deploy_file(path)

    res = discover_deploy_files(tmp_path_factory.getbasetemp())

    expected = generator(
        DeployFile(
            path=str(path),
            code=DUMMY_CONTENT,
        )
    )

    compare(res, expected)


def test_discover_deploy_files__find_files_in_nested_directories(tmp_path_factory):
    paths = [tmp_path_factory.getbasetemp() / "DEPLOY"]

    path = tmp_path_factory.mktemp("foo")
    paths.append(path / "DEPLOY")

    path = tmp_path_factory.mktemp("bar")
    paths.append(path / "DEPLOY")

    for path in paths:
        _create_dummy_deploy_file(path)

    res = discover_deploy_files(tmp_path_factory.getbasetemp())

    expected = [
        DeployFile(
            path=str(path),
            code=DUMMY_CONTENT,
        )
        for path in paths
    ]

    compare(
        sorted(res, key=lambda f: f.path),
        sorted(expected, key=lambda f: f.path),
    )


def test_discover_deploy_files__find_file_with_custom_name(tmp_path_factory):
    path = tmp_path_factory.getbasetemp() / "TREB"
    _create_dummy_deploy_file(path)

    res = discover_deploy_files(tmp_path_factory.getbasetemp(), "TREB")

    expected = generator(
        DeployFile(
            path=str(path),
            code=DUMMY_CONTENT,
        )
    )

    compare(res, expected)


def test_vars__exposes_keys_as_attributes():
    vars = Vars(
        {
            "foo": 1,
            "bar": "spam",
        }
    )

    compare(vars.foo, 1)
    compare(vars.bar, "spam")


def test_vars__raises_AtrributeError_if_key_does_not_exist():
    vars = Vars(
        {
            "foo": 1,
            "bar": "spam",
        }
    )

    with ShouldRaise(AttributeError):
        vars.spam
