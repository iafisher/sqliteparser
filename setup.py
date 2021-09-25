import os

from setuptools import find_packages, setup

dpath = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(dpath, "README.md"), "r") as f:
    long_description = f.read()


setup(
    name="sqliteparser",
    version="0.3",
    description="A parser for SQLite's dialect of SQL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Ian Fisher",
    author_email="iafisher@fastmail.com",
    packages=find_packages(exclude=["tests"]),
    install_requires=["attrs >= 20.3.0"],
    project_urls={"Source": "https://github.com/iafisher/sqliteparser"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: SQL",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Topic :: Database",
    ],
)
