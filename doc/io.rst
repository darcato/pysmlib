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
    :method:`connect()`, which returns an instance of this class.

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

    :returns: ``True`` if a previous (or no) :method:`put()` on this input has completed, ``False`` if a :method:`put()` is being executed in this moment.

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

Methods which detect edges
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Methods which detect trends
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _io-mapping:

I/O mapping and parametrization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Implementing a Naming Convention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~