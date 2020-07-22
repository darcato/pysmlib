# Python installation file
#
# TO INSTALL (user):
# pip install [-e] .
#
# TO UPLOAD NEW RELEASE (maintainer):
# 0 - Update CHANGELOG.md
# 1 - git tag <new_tag>
# 2 - python setup.py clean --all
# 3 - rm -rf dist
# 4 - python setup.py sdist bdist_wheel
# 5 - twine upload -r testpypi dist/*
# 6 - twine upload dist/*
# 7 - cd docs/ && make html
# 8 - git commit -am "Documentation update"
# 9 - git push github master

from setuptools import setup
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='pysmlib',
      version=versioneer.get_version(),
      description='Python Finite State Machines for EPICS',
      python_requires='>=3.6',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://darcato.github.io/pysmlib/docs/html/',
      download_url='https://github.com/darcato/pysmlib',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      install_requires=['pyepics'],
      zip_safe=False)
