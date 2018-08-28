.. _fsm-development:

===============================================
Finite State Machine development
===============================================

States execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  image:: /_static/images/pysmlib_states.png
    :align: center
    :width: 80%

Pysmlib handles all the logic to implement the execution of finite state machine
states. The user only has to implement the actual states, as methods of
:class:`fsmBase`. Each state can have up to 3 methods defined, for example for a
state called "exampleState" these are:

    ``exampleState_entry()`` [optional]
        This method is executed only once on the transition from previous state
        to the current one ("exampleState"). It can be useful for
        initializations or to perform specific actions related to the
        transition. For example if this is an error state, one could use the
        entry part of the error state to perform security actions (like power
        off the output of a power supply), and then wait on the ``eval``
        method for a manual reset of the error before continuing. If it is
        omitted the ``eval`` method is executed directly.

    ``exampleState_eval()`` [mandatory]
        This the the main body of the state, and the only mandatory part. If
        this method is defined, so is the state. If this is the current state,it
        is executed every time an event occurs on one of the FSM inputs. Here
        the code should check some conditions and when they are met, perform
        actions accordingly. These can be a ``put()`` to write a value to an
        output or a change of FSM state, by calling ``gotoState("nextStateName")``. The FSM  will remain in this state and execute this method until the first call to ``gotoState()``.

    ``exampleState_exit()`` [optional]
        This method is the opposite of the ``entry`` one and is execute only
        on the transition from this state to the next one, with no distinction
        on the destination. It can be used to perform some clean-up after the
        execution of the state and to perform actions related to this
        transition.
        
This architecture gives easy access to the first and last execution of the
state, which is often useful! Note that after the ``entry`` method the library
does not wait for an event to execute the ``eval`` one, but it is executed right
away. The same is true for the execution of the ``exit`` method after the
``eval``.


State definition example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In this example we will see how to program a FSM state will all the three
methods available.

The goal of this snippet of code is to achieve a motor movement and wait for its
completion before continuing to the next state. Some of the code functionality
are explained on the next pages of this documentation. ::

    #######################################################################
    # MOVE state
    
    # Entry method: executed only the first time
    def move_entry(self):
        steps = self.smallStep.val()            # get steps to move from a PV
        self.logI("Moving %d steps..." % steps) # write to info log
        self.motor.put(steps)                   # motor record PV - this will move the motor
        self.tmrSet('moveTimeout', 10)          # Set a timer of 10s

    # Eval method: executed for each event until gotoState() is called
    def move_eval(self):
        if self.doneMoving.rising():            # If the motor movement completed
            self.gotoState("nextState")         # continue to next state
        elif self.tmrExp("moveTimeout"):        # Timer expired event
            self.gotoState("error")             # go to an error state
            self.logE("The movement did not complete before timeout reached")   #write to error log
    
    # Exit method: executed only the last time
    def move_exit(self):
        self.logD("Motor status word is: %d" % self.motorStatus.val()) # write to debug log

    #######################################################################

.. _event-types:

Event types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The events which trigger the execution of the current state are:

    Connection events
        One of the input has connected or disconnected.

    Change events
        One of the inputs has changed value.

    Put complete events
        When a call to ``put()`` is executed the value has to be written over
        the network to the PV. This may take some time and after that the put
        complete event is notified. When executing a ``put()`` on some kinds of
        PVs, these are executed. The event is returned when the execution has
        completed.
    
    Timer expired events
        These events are local of pysmlib and are used to notify the current
        state that a previously set timer has reached its maximum time.

There are only two situations where a new state is executed without being
triggered by an event:

    1. The first state is evaluated once at startup.
    2. When a transition from a state to the next one occurs, the next one is   evaluated once right after the previous one, without waiting for an event.

In these cases, all the methods on the inputs which detect edges
(:ref:`io-edges`) return false.


:class:`fsmBase` class reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: fsmBase (name[, tmgr=None[, ios=None[, logger=None]]])
    
    Create an empty FSM: usually you derive from this to add custom states. 

    :param name: the name of the FSM and its related thread.
    :type name: string
    :param tmgr: a timer manager instance
    :type tmgr: :class:`fsmTimers` object
    :param ios: a container of all the (shared) I/Os available
    :type ios: :class:`fsmIOs` instance
    :param logger: a log facility
    :type logger: :class:`fsmLogger` instance

    The optional arguments let you pass shared objects. When they are omitted,
    they are automatically created by :class:`fsmBase` from default classes,
    while derivate ones can be passed. Usually just one instance of the three
    classes is shared between all the FSMs on an executable. The :ref:`loader`
    automatically takes care of these arguments.

.. method:: gotoState (stateName)

    Force a transition from the current state to "stateName". First of all the
    ``exit`` method of the current state is executed, then the library will
    look for the three methods associated to the string "stateName", as
    described above, will execute the ``entry`` and ``eval`` method, then
    wait for an event. When this arrives, the ``stateName_eval`` method is executed again.

    :param stateName:  the name of the next state
    :type stateName:  String

.. method:: gotoPrevState ()

    Return to the previous state

.. method:: fsmname ()

    Return the FSM name
    
    :returns: FSM name.

.. method:: logE (msg)

    Write to log with ERROR verbosity level = 0.

    :param msg: the log message
    :type msg: string

.. method:: logW (msg)

    Write to log with WARNING verbosity level = 1.

    :param msg: the log message
    :type msg: string
    
.. method:: logI (msg)

    Write to log with INFO verbosity level = 2.

    :param msg: the log message
    :type msg: string
    
.. method:: logD (msg)

    Write to log with DEBUG verbosity level = 3.

    :param msg: the log message
    :type msg: string
    
.. method:: connect (name[, **args])

    :param name: the PV name, or the map reference to a PV name.
    :type name: string
    :param args: optional arguments to be passed to :meth:`fsmIOs.get()`
    :returns: :class:`fsmIO` object

    The optional arguments can be used by :class:`fsmIOs` derivate classes to
    get further specification on the desired input. See :ref:`io-mapping`.

.. method:: start ()

    Start FSM execution.

.. method:: kill ()

    Stop FSM execution. FSM are derivate of :class:`threading.Thread` so they
    cannot be restarted after a kill, but a new instance must be created.
    However, a better approach is to use an idle state where the FSM will do
    nothing, instead of killing it.

.. method:: tmrSet (name, timeout[, reset=True])

    Create a new timer which will expire in `timeout` seconds, generating an
    timer expired event, which will execute the FSM current state (at expiration
    time).

    :param name: A unique identifier of this timer. The same timer can be reused more than once recalling the same name.
    :type name: string
    :param timeout: The expiration time, starting from the invocation of :meth:`tmrSet`. [s]
    :type timeout: float
    :param reset: If this is ``True`` the timer can be re-initialized before expiration. Default = ``True``.
    :type reset: boolean

.. method:: tmrExp (name)

    This will return ``True`` if the timer has expired or does not exist.
    
    :returns: timer expired condition

.. method:: isIoConnected ()

    This will return ``True`` only when all the FSM inputs are connected,
    meaning that they have received the first connection event.

    :returns: ``True`` if all I/Os are connected.

.. method:: setWatchdogInput (input[, mode="on-off"[, interval=1]])

    This set an input to be used for the :ref:`watchdog` logic.
    
    :param input: the input to use as watchdog.
    :type input: :class:`fsmIO` object.
    :param mode: One of "on-off", "off", "on".
    :type mode: string
    :param interval: the watchdog period [s].
    :type interval: float
    :raises: ValueError: Unrecognized input type or mode.

.. method:: getWatchdogInput ()

    Returns the input set as a watchdog or ``None``.

    :returns: watchdog input or ``None``.