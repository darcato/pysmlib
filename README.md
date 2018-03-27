# pysmlib
--------------------
## A python library for creating EPICS finite state machines, running in different threads as daemons and sharing resources.

_Developers_: Damiano Bortolato - Davide Marcato

Laboratori Nazionali di Legnaro - INFN

## Introduction

### Main features

## Installation
To install simply run:

```
sudo pip install pysmlib
```

or download the latest release/sources from github, unpack it and run:

```
cd pysmlib
pip install .
```

### Dependencies
As of today only python 2.7 is supported. pyepics and numpy modules are required and automatically installed by pip. 
To work properly pyepics needs to find the correct path to you EPICS installation, so you need to add the following line to your bashrc file:

```
export PYEPICS_LIBCA=<path_to_your_epics_base>/lib/linux-x86_64/libca.so
```
replacing ``` <path_to_your_epics_base> ``` with the path to the folder containing your compiled EPICS base.

For more information about pyepics visit http://cars9.uchicago.edu/software/python/pyepics3/

## Documentation

### Creating the fsm

### Accessing I/O

### Logger

### Loader and fsm execution

### Timers

### Watchdog

### Advanced

