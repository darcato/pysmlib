.. _pysmlib-overview:

===============================================
Pysmlib overview
===============================================

This section will describe the standard workflow to go from an empty file 
editor to a running finite state machine with pysmlib. Each step will be then 
explained in detail in the following sections of this documentation.


Define your FSM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pysmlib lets you create finite state machines, so the first step is
to adapt your algorithm to a fsm design. This means identifying all
the states required and the conditions that trigger a transition from
one state to another. Furthermore, all the required input and outputs
must be identified: the input are usually needed to determine the
current state and receive events, while the outputs are used to
perform actions on the external world.

The library is designed to be connected to EPICS PVs, so EPICS IOCs must be
running with the required PVs, otherwise the FSM will sleep waiting for the PVs
to connect.

General structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Each finite state machine is created as a derived class from :class:`fsmBase`,
which is part of pysmlib. ::
    
    from smlib import fsmBase

    class exampleFsm(fsmBase):
        def __init__(self, name, *args, **kwargs):
            super(exampleFsm, self).__init__(name, **kwargs)

In this snippet of code the class is declared and the parent class is
initialized, passing a ``name`` as argument which identifies the
class instance. In fact, when this code will be executed a new thread
will be created for each instance of the class.

.. note:: Never forget to include ``**kwargs`` in the arguments of the super class as they are used by the :mod:`loader`.

Define inputs / outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the class constructor the I/O must be defined. Note that there is
no actual distinction between a input and a output, both can be read
and written, the only difference is how they will be used. For this
reason the term "input" can be used to indicate both. ::

    self.counter = self.connect("testcounter")
    self.mirror = self.connect("testmirror")
    self.enable = self.connect("testenable")

The :meth:`connect()` methods requires a string as argument, which is
the name of the EPICS PV to be connected (optional arguments are
available, see :class:`fsmIO`). 

Now the inputs will be connected and all their events will be evaluated.
This means that whenever one of those changes its status, the current
state of the FSM will be executed, in order to reevaluate the
conditions to perform an action or to change state.

At the end of the constructor the user must select the first state to
be executed when the fsm is run. ::

    self.gotoState('idle')

Implement states
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The states are simply defined as class methods, with a special
convention on their names. The basic way of naming them is to give the
desired name, plus ``_eval``. For example the ``idle`` state can be
defined like this::

    def idle_eval(self):
        if self.enable.rising():
            self.gotoState("mirroring")

In this case the FSM will execute this state whenever an input changes
its value and the condition at the second line is evaluated. The
``rising()`` method will return true only when the enable input (which
must be a binary PV, with a boolean value) goes from 0 to 1. In that
case a transition is triggered and when the next event will arrive,
the state called ``mirroring`` will be executed instead of ``idle``.
In all the cases where the ``rising()`` method returns false, nothing
will happen and the FSM will remain on the same state.
:ref:`fsm-development` describes more in detail the states execution mechanism.

Then other states can be defined, for example::

    def mirroring_eval(self):
        if self.enable.falling():
            self.gotoState("idle")
        elif self.counter.changing():
            readValue = self.counter.val()
            self.mirror.put(readValue)

Here other methods to access the I/O are presented: 

    ``val()``
        It returns the input value.

    ``put()`` 
        writes a value to an output.
    
    ``falling()`` 
        It is the opposite of ``rising()`` and returns true when a
        falling edge is detected

    ``changing()``
        It returns true when the FSM has been executed because the
        input has changed its value.

The resulting effect is that, while enabled, this FSM will read
the value of one input as soon as it changes and write it to another input.
For a complete description of the available methods see :class:`fsmIO`.


Load and execute the FSM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The best approach with FSMs is to keep them simple and with a specific goal, so
multiple instances of the same machine may have to be run with different
parameters, or even multiple different machine can be loaded to implement
multiple algorithms. Pysmlib has been design to offer greater efficiency when
multiple FSMs are loaded together on the same executable, because some resources
can be shared (eg: common inputs).

For these reasons a convenient loader class is available. The ``load()``
method lets you load an instance of your FSM with specific
parameters. At the end the execution begins with the method
``start()``::

    from smlib import loader

    l = loader()

    ## -------------------
    # load each fsm
    ## -------------------
    l.load(exampleFsm, "myFirstFsm")

    ## -------------------
    # start execution
    ## -------------------
    l.start()

Now you can execute the FSM simply launching::

    python exampleFsm.py

From this moment all the finite state machines will be running until a
kill signal is received (Ctrl-C). This creates an always-on daemon:
for this reason at the end of its algorithm an FSM should not exit
but simply go back to an idle state.

More options can be found at :ref:`loader`.


Complete example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Here is the complete example described in this section:

.. literalinclude:: ../examples/exampleFsm.py
        :language: python

This code is also available in the examples folder.