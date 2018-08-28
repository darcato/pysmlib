from setuptools import setup
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()


setup(name='pysmlib',
      version=versioneer.get_version(),
      description='A library to create event driven finite state machines for EPICS, running as daemons and sharing resources',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/darcato/pysmlib',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      install_requires=['pyepics', 'numpy'],
      zip_safe=False)