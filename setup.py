# Python installation file
# 
# TO INSTALL (user):
# pip install [-e] .
#
# TO UPLOAD NEW RELEASE (mantainer):
# 1 - git tag <new_tag>
# 2 - python setup.py clean --all && python setup.py sdist bdist_wheel
# 3 - twine upload dist/*
# 4 - cd docs/docs/ && make html
# 5 - git commit -am "Documentation update"
# 6 - git push github master

from setuptools import setup
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='pysmlib',
      version=versioneer.get_version(),
      description='Python Finite State Machines for EPICS',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://darcato.github.io/pysmlib/docs/html/',
      download_url='https://github.com/darcato/pysmlib',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      install_requires=['pyepics', 'numpy'],
      zip_safe=False)
