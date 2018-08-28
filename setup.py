from setuptools import setup
import versioneer

setup(name='pysmlib',
      version=versioneer.get_version(),
      description='A library to create event driven finite state machines for EPICS, running as daemons and sharing resources',
      url='https://baltig.infn.it/epicscs/pysmlib',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      install_requires=['pyepics', 'numpy'],
      zip_safe=False)