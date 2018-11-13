.. _timers:

===============================================
Timers
===============================================

How to use timers
~~~~~~~~~~~~~~~~~~~

The FSM execution, as explained on :ref:`fsm-development`, is event-driven. This
means that no code will be executed, until an event (eg: an input changes its
value) triggers the execution of the current state.

In some situations you may want to run some code at a specific time,
independently from the inputs. For example you may want to run periodic actions
with fixed delay, or wait for "timeout" delays. For these reasons the timers
have been introduces: they let you develop a FSM with asynchronous execution
model.

The basic usage can be seen in the following example::

    def move_entry(self):
        self.motor.put(100)                     # move the motor
        self.tmrSet('moveTimeout', 10)          # Set a timer of 10s

    def move_eval(self):
        if self.doneMoving.rising():            # If the motor movement completed
            self.gotoState("nextState")         # continue to next state
        elif self.tmrExpired("moveTimeout"):        # Timer expired event
            self.gotoState("error")             # go to an error state

As seen in the example, timers are available as methods of the :class:`fsmBase`
class. After moving the motor, a timer is set with :meth:`tmrSet` which means
that after 10 seconds a special event will be generated and the method
:meth:`tmrExpired` will return ``True``. This way the user can perform
appropriate actions when a movement takes too long to complete.

.. warning:: The :meth:`tmrExpired` method returns ``True`` even before the timer is set, and will continue to return ``True`` after expiration until it is set again.

Timers are identified with a string, which should be unique. When reusing the
same string, the same timer is used and if it is not expired, it is restarted.
To avoid it being restarted, use a third optional parameter of :meth:`tmrSet`:
``reset`` and set it to ``False``.


:class:`fsmTimers` class
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: fsmTimers()

    This class handles all the timers of all the FSMs as shared resources. It
    can be used by creating an instance and passing it as an optional argument
    to all the FSMs, or (better) using the :mod:`loader` which automatically
    manages it.