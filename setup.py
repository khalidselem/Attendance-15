from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in attendance/__init__.py
from attendance import __version__ as version

setup(
	name="attendance",
	version=version,
	description="Attendance",
	author="Peter Maged",
	author_email="eng.peter.maged@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
