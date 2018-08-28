.. pysmlib documentation master file, created by
   sphinx-quickstart on Wed Mar 28 11:50:32 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Python Finite State Machines for EPICS
======================================

Pysmlib is a Python library which helps creating event based finite state machines 
(fsm) for `Epics Control System <http://www.aps.anl.gov/epics/>`_. Each fsm 
runs in a different thread and, by default, continues its execution until explicitly
stopped. A convenient loader is provided to help loading multiple fsm together,
thus creating an always-on daemon. Full integration with Epics Channel Access 
protocol is provided via `PyEpics <http://cars9.uchicago.edu/software/python/pyepics3/>`_. 
The user can connect to Process Variables by defining an fsm input / output (I/O)
and can therefore access its values and changes via convenient methods. The fsm
current state is executed every time one of the connected inputs changes its value
or its connection state, so that the user can evaluate the actions to be 
performed, including changing state. In some cases, the user may want to execute 
some actions after a certain amount of time (eg: when a timeout expires) and so 
the library includes a timer facility which execute the current state after the
specified delay. Other useful features include a simple way to print logs in an
unified way and the possibility to register a specific I/O as watchdog, meaning
that the fsm will automatically write it periodically, so that external systems
can be informed of the online or offline status of the fsm daemon. 

The library is designed with network efficiency and system responsiveness 
in mind: it's usually important to act as soon as possible upon the change of an 
input, without overflowing the network with useless traffic. This is achieved
by choosing the daemon-like execution, which is the obvious choice in
case of always-on algorithms (eg: a PID) but can be used also for one time
procedures. In fact, an fsm can remain in a idle state, where no action is
performed, until a certain condition is met (eg: a rising edge on the "enable"
input) and then start executing the procedure, finally returning to the idle 
state. This means that when the enable arrives, all the I/Os are already
connected and the fsm doesn't have to wait for all the connection times. The
downside here is the network overload due to many connections which remain active
for a long time. For this reason the I/Os are shared between all the fsm loaded
on the same daemon, so that the minimum number of connections is required. Then, 
when an event related to a certain PV arrives, the library executes all the fsm
using that input and guarantees that the input doesn't change during the state
evaluation and that two or more fsm don't interfere with each other. As a
result it's usually recommended to group all the fsm that use related I/Os
in a single daemon, just remember that each fsm is a python thread! 

For all these reasons, pysmlib is a great solution to develop high level 
automation and control systems in any facility using Epics. It enables
the user to focus on the algorithms to implement without worrying about low-level
problems.

Main features include:
----------------------
  - Easy to use and fast development of complex event based fsm - just code the states!
  - Full EPICS Channel Access integration via PyEpics.
  - High expandability as provided by all the libraries of Python.
  - Integrated configurables logging systems.
  - Convenient methods to access all the information on I/O.
  - Timers can be used to execute actions after a time delay.
  - Integrated watchdog logic.
  - Multi-threading: each fsm is executed on a different thread, sharing I/O.
  - Convenient loader to launch a daemon with multiple fsm.
  - Possibility to apply a configurable naming convention on I/O.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   overview
   fsm
   io
   logger
   loader
   timer
   watchdog
   advanced

