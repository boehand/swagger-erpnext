from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from swagger import __version__ as version

setup(
    name="swagger",
    version=version,
    description="Dynamic Swagger UI for ERPNext – with automatic CSRF token injection",
    author="boehand",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
