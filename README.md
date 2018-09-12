# pysmlib

## A python library to create EPICS finite state machines, running in different threads as daemons and sharing resources.

_Developers_: Damiano Bortolato - Davide Marcato

Laboratori Nazionali di Legnaro - INFN

Main Repository: https://github.com/darcato/pysmlib

Full documentation: https://darcato.github.io/pysmlib/docs/html/

### Main features

- Easy to use and fast development of complex event based fsm - just code the states!
- Full EPICS Channel Access integration via PyEpics.
- High expandability as provided by all the libraries of Python.
- Integrated configurable logging systems.
- Convenient methods to access all the information on I/O.
- Timers can be used to execute actions after a time delay.
- Integrated watchdog logic.
- Multi-threading: each fsm is executed on a different thread, sharing I/O.
- Convenient loader to launch a daemon with multiple fsm.
- Possibility to apply a configurable naming convention on I/O.

## Installation

To install simply run:

``` bash
pip install pysmlib
```

or download the latest release/sources from github, unpack it and run:

``` bash
cd pysmlib
pip install .
```

### Dependencies

As of today, only python 2.7 is supported. Pyepics and numpy modules are
required and automatically installed by pip. Sphinx and its theme "Read the
Docs" are required to build the documentation.

## Example

``` python
#! /usr/bin/python
from smlib import fsmBase, loader

# FSM definition
class exampleFsm(fsmBase):
    def __init__(self, name, *args, **kwargs):
        super(exampleFsm, self).__init__(name, **kwargs)

        self.counter = self.connect("testcounter") # connect to PV "testcounter"
        self.mirror = self.connect("testmirror")
        self.enable = self.connect("testenable")

        self.gotoState('idle')
    
    # idle state
    def idle_eval(self):
        if self.enable.rising() == 0:
            self.gotoState("mirroring")

    # mirroring state
    def mirroring_eval(self):
        if self.enable.falling() == 0:
            self.gotoState("idle")
        elif self.mirror.changing():
            readValue = self.mirror.val()
            self.mirror.put(readValue)

## -------------------
# load each fsm
## -------------------
loader.load(exampleFsm, "myFirstFsm")

## -------------------
# start execution
## -------------------
loader.start()
```
