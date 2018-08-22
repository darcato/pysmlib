.. _fsm-development:

===============================================
Finite State Machine development
===============================================

States execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

..  image:: /_static/images/pysmlib_states.png
    :align: center

Pysmlib handles all the logic to implement the execution of finite state machine
states. The user only has to implement the actual states, as methods of
``fsmBase``. Each state can have up to 3 methods defined, for example for a
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


fsmBase
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
