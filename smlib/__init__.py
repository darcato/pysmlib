from ._version import get_versions
__version__ = get_versions()['version']
del get_versions

__doc__ = """
   A python library for creating EPICS finite state machines, 
   running in different threads as daemons and sharing resources.

   version: %s
   Principal Authors:
      Damiano Bortolato <damiano.bortolato@lnl.infn.it> INFN, Laboratori Nazionali di Legnaro
      Davide Marcato <davide.marcato@lnl.infn.it> INFN, Laboratori Nazionali di Legnaro

== License:
   GPLv3 - This is free software; see the source for copying conditions.  There is NO
   warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

== Overview:
   Main features include:
    - Easy to use and fast deployment of complex event based fsm.
    - High expandability as provided by all the libraries of Python.
    - Integrated configurables logging systems.
    - Convenient methods to access all the information on I/O.
    - Timers can be used to execute actions after a time delay.
    - Integrated watchdog logic.
    - Multi-threading: each fsm is executed on a different thread, sharing I/O.
    - Convenient loader to launch a daemon with multiple fsm.
    - Possibility to apply a configurable naming convention on I/O.

""" % (__version__)

from .fsm import fsmBase
from .logger import fsmLogger, fsmFileLogger
from .timer import fsmTimers
from .io import fsmIOs, mappedIOs, fsmIO
from .fsmTemplate import fsmTemplate
from .fsmWatchdog import fsmWatchdog
from .loader import loader
