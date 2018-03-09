from setuptools import setup

setup(name='pysmlib',
      version='2.0.0',
      description='A library to create finite state machines running as daemons and sharing resources',
      url='https://baltig.infn.it/epicscs/pysmlib',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      install_requires=['pyepics'],
      zip_safe=False)