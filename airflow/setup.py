from setuptools import setup, find_packages
from os import path
import time

if path.exists("VERSION.txt"):
    # this file can be written by CI tools (e.g. Travis)
    with open("VERSION.txt") as version_file:
        version = version_file.read().strip().strip("v")
else:
    version = str(time.time())

setup(
    name='knesset-data-pipelines-airflow',
    version=version,
    packages=find_packages(exclude=['contrib', 'docs', 'tests*', 'dags']),
    entry_points={
        'console_scripts': [
            'knesset-data-pipelines = knesset_data_pipelines.cli:main',
        ]
    },
)
