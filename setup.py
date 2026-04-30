from setuptools import find_packages, setup

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="construction",
	version="0.1.0",
	description="Construction ERP App for BOQ, Cost Estimation, and Project Management",
	author="Mohamed Elrefae",
	author_email="melrefa3@hotmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	license="MIT",
)
