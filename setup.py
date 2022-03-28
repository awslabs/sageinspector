from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="sage-inspector",
    install_requires=[
        "boto3",
        "click >= 8.0",
    ],
)
