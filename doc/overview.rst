.. _pysmlib-overview:

===============================================
Pysmlib overview
===============================================

This section will describe the standard workflow to go from an empty file 
editor to a running finite state machine with pysmlib. Each step will be then 
explained in detail in the following sections of this documentation.


Define your FSM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``pysmlib`` lets you create finite state machines, so the first step is
to adapt your algorithm to a fsm design. This means identifying all
the states required and the conditions that trigger a transition from
one state to another. Furthermore, all the required input and outputs
must be identified: the input are usually needed to determine the
current state and receive events, while the outputs are used to
perform actions on the external world.


General structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Each finite state machine is created as a derived class from ``fsmBase``,
which is part of pysmlib. ::
    
    from smlib import fsmBase

    class exampleFsm(fsmBase):
        def __init__(self, name, *args, **kwargs):
            super(exampleFsm, self).__init__(name, **kwargs)

In this snippet of code the class is declared and the parent class is
initialized, passing a ``name`` as argument which identifies the
class instance. In fact, when this code will be executed a new thread
will be created for each instance of the class.


Define inputs / outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In the class constructor the I/O must be defined. Note that there is
no actual distinction between a input and a output, both can be read
and written, the only difference is how they will be used. For this
reason the term "input" can be used to indicate both. ::

    self.counter = self.connect("testcounter")
    self.mirror = self.connect("testmirror")
    self.enable = self.connect("testenable")

The ``self.connect()`` methods requires a string as argument, which is
the name of the EPICS PV to be connected (optional arguments are
available, see :ref:`accessing-io`). 

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
        if self.enable.rising() == 0:
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
        if self.enable.falling() == 0:
            self.gotoState("idle")
        else if self.mirror.hasChanged():
            readValue = self.mirror.val()
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
For a complete description of the available methods see :ref:`accessing-io`.


Load and execute the FSM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pysmlib has been developed with modularity in mind, so usually each
FSM is loaded multiple times with different parameters. For example,
imagine a FSM which executes a PID control on a power supply: you may
have multiple identical power supplies, so the code should be
parametric and multiple instances of the same FSM should be executed, one
for each power supply. This enables greater efficiency, in particular
over the network communications, because common inputs are shared.

For these reasons a convenient loader is available. The ``loader.load()``
function lets you load an instance of your FSM with specific
parameters. At the end the execution begins with the function
``loader.start()``::

    from smlib import loader

    ## -------------------
    # load each fsm
    ## -------------------
    loader.load(exampleFsm, "myFirstFsm")

    ## -------------------
    # start execution
    ## -------------------
    loader.start()

From this moment all the finite state machines will be running until a
kill signal is received (Ctrl-C). This creates an always-on daemon:
for this reason at the end of its algorithm the FSM should not exit
but simply go back to an idle state.

More options can be found at :ref:`loader`.

Complete example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Here is the complete example described in this section::

    from smlib import fsmBase, loader

    # FSM definition
    class exampleFsm(fsmBase):
        def __init__(self, name, *args, **kwargs):
            super(exampleFsm, self).__init__(name, **kwargs)

            self.counter = self.connect("testcounter")
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
            else if self.mirror.hasChanged():
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