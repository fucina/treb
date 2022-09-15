pex_binary(
    name="bin",
    entry_point="__main__.py",
    dependencies=[
        # force plugins to be included even if they are not directly used anywhere else in the codebase.
        "//src/treb/plugins/cloudflare/register.py",
        "//src/treb/plugins/docker/register.py",
        "//src/treb/plugins/gcp/cloudrun/register.py",
        "//src/treb/plugins/gcp/monitoring/register.py",
        "//src/treb/plugins/time/register.py",
    ],
)

python_sources()

docker_image(name="docker", image_tags=["commit-{build_args.GIT_COMMIT}"], repository="treb")
