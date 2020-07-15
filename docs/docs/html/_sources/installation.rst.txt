.. _Download-and-Installation:

====================================
Download and Installation
====================================

.. _pyepics:        http://cars9.uchicago.edu/software/python/pyepics3/
.. _Sphinx:         http://www.sphinx-doc.org/en/master/
.. _Read the Docs:  https://readthedocs.org/
.. _Github:         https://github.com/darcato/pysmlib


Prerequisites
~~~~~~~~~~~~~~~
This package requires Python version 3.6+. 
One module is mandatory: `PyEpics`_ which provides the 
EPICS Channel Access support. It is automatically installed when using pip, 
but you may have to install the EPICS base on your system and configure `PyEpics`_ to 
locate ``libca``. See `PyEpics`_ documentation for further details.

`Sphinx`_ and its theme `Read the Docs`_ are required to build this 
documentation.


Downloads and Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To install, try running::

    pip install pysmlib

Installing from sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Alternatively, if you want to install from sources::

    pip install git+https://github.com/darcato/pysmlib.git@latest

where you can replace ``latest`` with the desired git tag.

Another option is to download the tarball from `Github`_, extract it and 
then run::

    cd pysmlib
    pip install . 


Getting Started
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Check if the installation was successful by executing::

    >>> import epics
    >>> epics.ca.find_libca()

This will print the path of the ``libca`` which will be used. If any error
occurs, then check the installation of `PyEpics`_. If you already have EPICS
base compiled on your system you can choose to use its ``libca`` adding the following line to your ``~/.bashrc`` file::

    export PYEPICS_LIBCA=<path_to_your_epics_base>/lib/linux-x86_64/libca.so

replacing ``<path_to_your_epics_base>`` with the path to the folder containing your compiled EPICS base.

Moreover you should now be able to import the ``smlib`` package without errors::
    
    >>> import smlib

To start creating your first finite state machine you can give a look at the 
examples provided with the package (eventually executing them) and read 
:ref:`pysmlib-overview`.


Testing
~~~~~~~~~~~~~
**Still in development**

Automatic testing is done with gitlab-ci, which starts a Docker image, installs
pysmlib with all its dependencies, run a simple IOC and executes the test suite.
This can be done for different versions of python. In addition the user can
execute the gitlab-ci script locally or simply run the test suite on his system.

**TODO**: Add specific instructions.


Development Version
~~~~~~~~~~~~~~~~~~~~~~~~

To contribute to the project you can fork it on `Github`_, any help is appreciated!
To obtain the latest development version just clone the project::

    git clone https://github.com/darcato/pysmlib.git
    cd pysmlib
    pip install -e .

where the ``-e`` automatically updates the installed version when the local
repository is updated.


Getting Help
~~~~~~~~~~~~~~~~~~~~~~~~~

For questions, bug reports, feature request, please consider using the
following methods:

1.  Create an issue on `Github`_ where it can be discussed. 

2.  Send an email to Davide Marcato <davide.marcato@lnl.infn.it>, or 
    to the Tech Talk mailing list if the issue is related to EPICS.

3.  If you are sure you have found a bug in existing code, or have
    some code you think would be useful to add to pysmlib, consider
    making a Pull Request on `Github`_.


License
~~~~~~~~~~~~~~~~~~~
The whole project is released under the GPLv3 license.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

Acknowledgments
~~~~~~~~~~~~~~~~~~~~~~
Pysmlib has been written by Damiano Bortolato <damiano.bortolato@lnl.infn.i> 
and Davide Marcato <davide.marcato@lnl.infn.it> at Legnaro National Laboratories,
INFN. The development started in 2016 in order to have a simpler alternative to
the Epics sequencer to create high level automation for the RF control
system of the ALPI accelerator. After that it has been separated in a standalone library to be used for the whole SPES project.
