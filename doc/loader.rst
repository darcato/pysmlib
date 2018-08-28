.. _loader:

===============================================
Loader and fsm execution
===============================================

The loader is provided help the user create a single launcher of many FSMs
sharing resources. All the configuration options are available via convenient
methods. It takes care of instantiating the classes for loggers, timers, and
shared inputs and all the instances of the user defined FSM as required.

:mod:`loader` module
~~~~~~~~~~~~~~~~~~~~~~~

.. module:: loader

.. function:: loader.setVerbosity(level)

    :param level: The verbosity level: all the messages with lower or equal level are printed.
    :type level: int

.. function:: loader.setVerbosity(levelStr)

    :param levelStr: The verbosity level, one of "error", "warning", "info","debug".
    :type level: string

    The available verbosity levels are:
        
        * Error: these messages are always printed, and contain critical information on failures.
        * Warning: these messages are printed only when the verbosity level is 1 or higher.
        * Info: these messages are printed only when the verbosity level is 2 or higher 
        * Debug: these messages are printed only when the verbosity level is 3 or higher. They contain a lot of detailed information useful while debugging applications.
    
.. function:: loader.logToFile(path, prefix)

    :param path: The path of a directory where to store all the logs. Can be both relative or absolute.
    :type level: string
    :param prefix: A prefix for log file names, to identify all the logs belonging to this executable.
    :type prefix: string

    While logging to file, a file will be created for each FSM loaded, plus one
    more for all the information on the main thread. If this function is called,
    the logger will be instantiated from :class:`fsmFileLogger` instead of the
    default one (:class:`fsmLogger`).

.. function:: loader.setIoMap(ioMapPath)

    :param ioMapPath: The path of a file defining a map for the inputs. See :class:`mappedIOs`.
    :type ioMapPath: string

.. function:: loader.load(myFsmClass, name, ... )

    :param myFsmClass: The definition of a FSM.
    :param name: The unique name of this FSM instance.
    :type name: string

    This function is used to load multiple FSM in this executable. The first
    parameter is the FSM class, not one of its instances. In fact, the loader
    will create the instance, adding the required optional arguments to the
    constructor. Then an arbitrary number of parameters can be passed, as
    required by each different FSM constructor.

.. function:: loader.start()

    This is usually the last function to be called: it starts the execution of
    all the loaded FSMs and suspends the main thread, waiting for a signal.

    The supported signals are::

        * SIGINT (Ctrl-C): Terminate the execution of all the FSMs.
        * SIGUSR1: Print a report of all the inputs connections.

    In this way each FSM is executed in a separate thread until the kill signal
    is received.

Example
~~~~~~~~~~~~~~~~~~~~~~~

::

    from smlib import loader
    from myfsm import myfsm

    ## -------------------
    # logger options
    ## -------------------
    loader.setVerbosity("debug")  ##use only this if you want to print log to shell
    loader.logToFile("mypath", "daemon")  ##use also this if you want to print to file

    ## -------------------
    # inputs options
    ## -------------------
    loader.setIoMap("pathToMapFile")  #this will set the map file path

    ## -------------------
    # load each fsm
    ## -------------------
    loader.load(myfsm, "fsm1", "ciao", "come", "va?")
    loader.load(myfsm, "fsm2", "ciao")

    ## -------------------
    # start execution
    ## -------------------
    loader.start()

How to run the application
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All the parameters are specified via the loader, so you can easily run the
application with python. For example, if the example above is saved on a file
named ``myDaemon.py``, you can execute it with::

    python myDaemon.py

and it can be stopped by the ``Ctrl-C`` key combination or (on linux) with::

    pkill -SIGINT -f myDaemon.py

If you want to print a report on the connected inputs, during execution run::

    pkill -SIGUSR1 -f myDaemon.py

and check logs for the output. This will not affect FSM execution.
