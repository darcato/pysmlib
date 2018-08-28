.. _watchdog:

===============================================
Watchdog
===============================================

When using pysmlib all the FSM logic is not directly connected to the EPICS IOC
as is the case for the EPICS sequencer. This means that if the pysmlib
executable crashes or it loses network connection, all the FSM logic will stop
to work, while the IOC continues to live without noticing it. In some cases this
can be a problem and you may want at least to trigger a warning for someone to
check the situation. For this reason a mechanism has to be implemented to inform
the IOC about the "online" status of the FSM executable.

An easy way of doing it is to implement a `watchdog` logic, that is define a
special input where to perform a periodic :meth:`put` and signal an "offline"
status when no :meth:`put` is received for a time longer than the period.

IOC side: definition of the PV
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For this purpose a special kind of PV can be used: a binary output. This
particular record type has a field called ``HIGH`` which sets the time its value
must remain high (that is to 1) after receiving a ``put(1)``. So, it is
sufficient to write to it from a FSM with a smaller period to keep it always at
1. Then, if the value goes to 0 the FSM is recognized as offline.

The PV (one for each FSM) can be defined like this::

    #watchdog
    record (bo, "watchdog") {
        field (DESC, "FSM watchdog")
        field (DTYP, "Soft Channel")
        field (DOL, 0)
        field (HIGH, 20)  # keep the 1 value for 20s after the put
        field (PINI, 1)
        field (ZNAM, "Disconnected")
        field (ONAM, "Connected")
    }

Refer to the EPICS documentation for more informations on how to define PVs
inside an IOC.

FSM side: the watchdog input
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To signal being online each FSM has to perform periodic :meth:`put` to its
watchdog PV. This can be easily achieved with the :meth:`setWatchdogInput`
method of :class:`fsmBase`: it is sufficient to pass to it a standard input
(created with :meth:`connect`) and set two parameters:

    1. The watchdog mode, which can be:
        a. "on-off": A ``put`` is performed periodically, once to 1 and once to 0.
        b. "off": A ``put(0)`` is performed periodically.
        c. "on": A ``put(1)`` is performed periodically.
    2. The watchdog period in seconds.

Example
^^^^^^^^^^^^
In the following example the input ``wdog`` is used as watchdog. A ``put(1)``
will be automatically performed to it every 5s, as long as the FSM is running.

::

    class exampleFsm(fsmBase):
        def __init__(self, name, *args, **kwargs):
            super(exampleFsm, self).__init__(name, **kwargs)
            
            self.wdog = self.connect("exampleWdog")
            self.setWatchdogInput(self.wdog, mode="on", interval=5)
        
        ...
