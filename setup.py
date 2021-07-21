from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in payroll_addons/__init__.py
from payroll_addons import __version__ as version

setup(
	name='payroll_addons',
	version=version,
	description='addons untuk payroll',
	author='das',
	author_email='das@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
