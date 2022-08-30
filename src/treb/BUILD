pex_binary(
    name="bin",
    entry_point="__main__.py",
    dependencies=[
        # force plugins to be included even if they are not directly used anywhere else in the codebase.
        "//src/treb/plugins/docker/register.py"
    ],
)

python_sources()

docker_image(
    name="docker",
)
