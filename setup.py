from setuptools import setup, find_packages
import os, time

if os.path.exists("VERSION.txt"):
    # this file can be written by CI tools (e.g. Travis)
    with open("VERSION.txt") as version_file:
        version = version_file.read().strip().strip("v")
else:
    version = str(time.time())

# Run
setup(
    name="knesset-data-pipelines",
    version=version,
    packages=find_packages(exclude=["tests", "test.*"]),
    install_requires=["datapackage-pipelines", "knesset-data==2.1.5", "fuzzywuzzy[speedup]"],
    extras_require={'develop': ["tox", "pytest"]},
    url='https://github.com/hasadna/knesset-data-pipelines',
    license='MIT',
    entry_points={
      'console_scripts': [
        'dpp_send_metrics = datapackage_pipelines_knesset.cli:dpp_send_metrics',
      ]
    },
)
