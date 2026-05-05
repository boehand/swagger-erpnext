from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from erpnext_api_docs import __version__ as version

setup(
    name="erpnext_api_docs",
    version=version,
    description="Generic CRUD REST endpoints for every ERPNext DocType",
    author="boehand",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
