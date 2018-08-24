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
methods. These are divided in four macro categories:

    * Methods to access stationary conditions
    * Methods to detect edges.
    * Methods to detect trends
    * Methods to write outputs


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

So, this way these methods return ``True`` just for one state evaluation, when a
certain event is happening `right now`, and let the user access the information
on rising or falling edges on certain conditions. This is useful when an action
has to be performed only once when an event occurs, and not each time a  
condition is true.

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
The inputs on pysmlib are shared resources. The class which groups all the
inputs from all the FSMs is:

.. class:: fsmIOs ()

    This is a container of all inputs of all FSMs. It can be instantiated by the
    user and passed to all the FSMs as a optional argument (``ios``, see
    :class:`fsmBase`) on their constructor, but the easiest way is to use
    the :ref:`loader` which automatically handles FSM optional arguments.

    This class declares a method ``get()`` which receives a string with the
    input name, creates the corresponding input, if not already available,
    and returns it. It is used by :meth:`connect()` and should not be accessed
    directly.

Using the :class:`fsmIOs` each input name must be exactly a PV name. This
approach has some disadvantages:

    1. The PV name is hard-coded in the FSM implementation. If, for any reason,the PV name changes, the code must be modified!!
    2. The names are not parametric. If your logic works well for two identical objects, with PV names which differ only for a number (eg: PS01 vs PS02) you will have to implement manually a parametrization mechanism for each FSM.
    3. Inserting long PV names in the code is not much readable.
    4. The user has to check each PV name to be compatible with the Naming Convention of the facility, if present.

For all these reasons a derivate class of :class:`fsmIOs` has been developed.

.. class:: mappedIOs (mapFile)

    :param mapFile: the path to a map file, whose syntax is described below.
    :type mapFile: string

This let you use short names to identify inputs, and add any number of optional
arguments to specify custom parameters. For example, you can define an input
like this::

    class exampleFsm(fsmBase):
        def __init__(self, name, psNum, *args, **kwargs):
            super(exampleFsm, self).__init__(name, **kwargs)
            
            self.ps = self.connect("powerSupply", n=psNum)

This way, the number of the power supply is a parameter of the FSM and you can
instantiate multiple FSMs, one for each power supply. Moreover, inside the code
the "powerSupply" string is easy to read and 

Then the input name has to be somehow translated to the correct PV name, which
is, in our example, "PS01". For this reason a map file has to be defined,
containing the following lines::

    > pattern = ({:.2s}{:02d}) (OBJ, NUM)
    "powerSupply" = "PS", <n>      #this is a comment

As you can see the first thing to do is to define a pattern, which is the naming
convention followed by all the PVs who are defined after (before the next
pattern). In this case the pattern specify that the PV name must contain two
characters, followed by an integer with 2 digits, with leading zeroes. This way
the translator knows what to expect, can correctly format numbers and can check
that the inputs respect this Naming Convention. The syntax of the pattern
definition is the same as the one used by python :func:`format()` function.

The second line defines the string "powerSupply": this is the string that we
will use inside our code to refer to that particular input. After the equal mark
we can find the informations to fill the pattern to create the PV name. In
particular the first two characters are provided directly: "PS". Note that the
quotation marks are optional and will be stripped away. The second part
instead, which is put inside the ``< >`` signs, represent a parameters. This
means that its value is not know before run time, and must be passed as an
optional argument (with the exact same name) to the :meth:`connect` method. In
fact, we provided the optional argument ``n``. So, at execution time the
translator will format the number as required, concatenate it to the first two
characters and obtain "PS01". This offer great flexibility to connect to similar
PVs who differ only for some counters.

A more complete example of a map file is the following one::

    #MACROS DEFINITION:
    > FAC = "Al"
    > APP = "Llrf"
    > SAPP = "Cryo"
    > CHID = "A"
    > OBJ = "Qwrs"
    > AMP = "Ampl"
    > CVON = "Cvon"
    > CRYG = "Cryg"

    #LONG PVS:
    > pattern = ({:.2s}{:.4s}{:.4s}{:02d}{:.1s}_{:.4s}{:02d}{:.1s}{:s}) (FAC, APP, SAPP, NSAP, CHID, OBJ, NOBJ, TYPE, SIGNAL)
    "CvonEn"             = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "ProcEn"         #enable fsm
    "CvonRetc"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "Retc"           #fsm return code
    "CvonMsgs"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "Msgs"           #message to user
    "CvonStat"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "Stat"           #state of the fsm
    "CvonRunn"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "Runn"           #running status the fsm
    "CvonWdog"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), $(CVON), <nobj>, ":", "Wdog"           #state of the fsm

    #SHORTER PVS
    > pattern = ({:.2s}{:.4s}{:.4s}{:02d}{:.1s}{:.1s}{:s}) (FAC, APP, SAPP, NSAP, CHID, TYPE, SIGNAL)
    "cryoName"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), ":", "Name"                           #cryostat string name
    "cryoNext"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), ":", "Next"                           #pointer to next cryostat
    "cryoPrev"           = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), ":", "Prev"                           #pointer to prev cryostat
    "cryoNQwrs"          = $(FAC), $(APP), $(SAPP), <nsap>, $(CHID), ":", "Nqwr"                           #n of qwr in this cryostat
    "cryogEn"            = $(FAC), $(CRYG), $(SAPP), <nsap>, $(CHID), ":", "RfpaEn"                        #enable from cryogenic 
    "storeConnWd"        = $(FAC), $(APP), , , , ":", "StorWd"                                             #store fsm connection watchdog

Syntax rules:

    * The character ``#`` is used for comments.
    * The character ``>`` signal special lines.
        * The word ``pattern`` is reserved to define a new pattern on special lines.
        * All the other cases are macro definitions.
    * Each normal line defines a input name and its link to a PV name.
        * The ``$( )`` string means that the part inside parentesis is a macro name and should be replaced with its value
        * The ``< >`` string indicates a parameter that should be passed as optional argument of :meth:`connect()`
    * Each element of the PV name is divided by a comma, and each part is associated with the one on the pattern, in order.

Macro definition is used to avoid repeting the same string everywhere in the
file, so each macro occurrence is substituted with its value on the whole
document. For example, having defined the marco ``> FAC = "Al"``, ``$(FAC)``
is replaced with ``Al``. 

Therefore, when defining an input, one of the string on the left can be used,
and then the PV name will be built concatenating all the pieces following the
pattern logic, and replacing the parameters with the values passed at run time.

Summary of the steps to implement a map on inputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    1. Use :class:`mappedIOs` instead of :class:`fsmIOs`. This is achieved by calling :func:`loader.setIoMap( )` function.
    2. Create the map file.
    3. Connect to the inputs using the strings defined in the map file, passing all the required parameters as optional arguments.