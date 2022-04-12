from setuptools import setup


def get_version_and_cmdclass(version_file):
    with open(version_file) as fobj:
        code = fobj.read()

    globals_ = {"__file__": str(version_file)}
    exec(code, globals_)

    return globals_["__version__"], globals_["cmdclass"]()


version, version_cmdclass = get_version_and_cmdclass(
    "src/sageinspector/_version.py"
)

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="sageinspector",
    version=version,
    install_requires=[
        "boto3",
        "click >= 8.0",
        "pydantic",
        "toolz",
    ],
    cmdclass={
        **version_cmdclass,
    },
)
