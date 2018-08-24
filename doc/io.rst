.. _accessing-io:

===============================================
Accessing I/O
===============================================
Input and Outputs are the only way to comunicate with the external world. In the
context of pysmlib each input is directly mapped to an EPICS PV. Furthermore the
term "input" is used as a generic term for I/O because each input can be also an
output. In fact, all the PVs can be read (get) and written (put).

The main class to access inputs is :class:`fsmIO`.

:class:`fsmIO` class reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. class:: fsmIO ( ... )
    
    This represent an input as an object. The constructor should be never called
    directly by the user. Each input is created with the method
    :meth:`connect()`, which returns an instance of this class.

The user can access the status of each input with some simple, yet powerful,
methods. These are divided in two macro categories: methods to access stationary
conditions and methods which detect edges.


.. _io-status:

Methods for stationary conditions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
These kind of methods return static informations about an input. For example
they can tell if an input is connected or not, but do not give any informations
on when the input has connected: it may have connected yesterday or just a
moment ago. 

.. method:: ioname ()

    :returns: the name of the input.

.. method:: val()

    :returns: the current value of the input.

.. method:: connected ()

    :returns: ``True`` if the input is connected, via Channel Access.

.. method:: initialized ()

    :returns: ``True`` if the input is connected and has received the first value, meaning its value is not ``None``.
    
.. method:: putComplete ()

    :returns: ``True`` if a previous (or no) :meth:`put()` on this input has completed, ``False`` if a :meth:`put()` is being executed in this moment.

.. method:: pval ()

    :returns: the previous value of the input.

.. method:: data (key)

    PyEpics PV objects contain more informations than value and connection
    status. To access those fields, use this method. The available key are listed
    here: <http://cars9.uchicago.edu/software/python/pyepics3/pv.html#user-supplied-callback-functions>

    :param key: the particular information to extract from a PV.
    :type key: string
    :returns: the requested information.

.. _io-edges:

Methods to detect edges
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
As described on :ref:`fsm-development`, while the FSM is running the current
state is executed exactly once for each event received on any of the FSM inputs,
or timers. With the methods on this group the user can access the information on
the reason why the FSM has been executed at each time. So, for example, if a
connection event is received, the FSM is executed and the method
:meth:`connecting()` on the correct input will return ``True`` for just this
execution. After that a change event is received, and the FSM is executed again:
this time the FSM was executed due to a change event, so :meth:`connecting()`
will return ``False``, but the input is still connected and so the
:meth:`connected()` will still return ``True``. In fact, this time the
method :meth:`changing()` will return ``True``.

So, this way these methods return ``True`` just once, when a certain event is
happening `right now`, and let the user access the information on rising or
falling edges on certain conditions. This is useful when an action has to be
performed only once when an event occurs, and not each time a condition is true.

.. method:: rising ()

    :returns: ``True`` if the input has just gone from 0 to not zero. Best to use only with boolean values (binary PVs).

.. method:: falling ()

    :returns: ``True`` if the input has just gone from not zero to 0. Best to use only with boolean values (binary PVs).
    
.. method:: changing ()

    :returns: ``True`` if the input has just changed its value.

.. method:: connecting ()

    :returns: ``True`` if the input has just connected.

.. method:: disconnecting ()

    :returns: ``True`` if the input has just disconnected. Note that the Channel Access uses timeouts to check the connection status, so a certain delay is to be expected.

.. method:: initializing ()

    :returns: ``True`` if the input has just received its first value after a connection.

.. method:: putCompleting ()

    :returns: ``True`` if the input has just completed a previous ``put()``.

Methods to detect trends
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In scientific applications, when an input has a physical meaning, it is often
useful to filter it, get average value or check the trend over a certain amount
of time. These methods cover most common use cases.

.. method:: setBufSize (numOfElements)

    This method has to be called at initialization, or before accessing the
    following methods. It creates a buffer of the required lenght where the read
    value are stored to be used as the input history.

    :param numOfElements: the buffer lenght
    :type numOfElements: int

    A successive call to this method will discard older buffer and create a new
    one, so transient effects can be observed. Numpy arrays are used.

.. method:: valAvg ()

    :returns: The average value of the elements on the buffer.

    Keep in mind that values are accumulated as they arrive, in a event driven
    way. This means that if a value does not change for a long time, no event is
    generated and the average value may be misleading. In other words: the
    values are not weighted with time.

.. method:: valStd ()

    :returns: Standard deviation of the elements on the buffer.

.. method:: valTrend ()

    :returns: 0 = flat, 1 = increasing, -1 = decreasing

    code::

        s = self._avbuf.std()                 # Standard deviation
        d = self._avbuf[0] - self._avbuf[-1]  # newer element - oldest element
        if d > s:
            return 1
        if d < -s:
            return -1
        return 0


Methods to write outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
At least, of course, this method can be used to write a new value to a output.

.. method:: put (newValue)

    Write `newValue` to output.

    :param newValue: the value to be written
    :type newValue: type depends on PV type
    :returns: ``False`` if :meth:`put()` failed, ``True`` otherwise. 

.. _io-mapping:

I/O mapping and parametrization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementing a Naming Convention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~