from setuptools import setup

setup(name='pysmlib',
      version='2.0.0',
      description='A library to create finite state machines running as daemons and sharing resources',
      #url='http://github.com/storborg/funniest',
      author='Damiano Bortolato - Davide Marcato',
      author_email='davide.marcato@lnl.infn.it',
      license='GPLv3',
      packages=['smlib'],
      zip_safe=False)