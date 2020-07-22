.. _logger:

===============================================
Logger
===============================================

All the log messages should be printed with the methods available in
:class:`fsmBase`. This ensures that they are threaded in a coherent way. In the
loader a verbosity level can be specified, so that only the messages with
verbosity level lower or equal to that are printed. For example a verbosity of
zero is related to ERROR logging, and messages are always printed, while a
higher verbosity may be useful only while debugging.

There are three options to log:

Log to Standard Output
~~~~~~~~~~~~~~~~~~~~~~~~~~~
This is the easiest method, and the default one if no other is specified. Should
be used only while developing or on small tests. All the messages are written to
the standard output of the console where the executable is launched.

This is achieved via a base class called :class:`fsmLogger`.

.. class:: fsmLogger ([level=3])

    Collect all the log messages from the various FSMs loaded and print them to
    stdout.

This can be used by creating an instance and passing it as an optional argument
to all the FSMs, or (better) using the :mod:`loader` with no option specified. The verbosity can be set with :func:`setVerbosity` function.


Log to File
~~~~~~~~~~~~~~~~~~~~~~~~~~~
A better approach is to write logs to file, in order to open them only when
needed. For this reason a derivate class of the previous one has been developed:

.. class:: fsmFileLogger ([level=3[, directory="logs/"[, prefix=""]]])

    :param level: the log level
    :type level: int
    :param directory: the folder where all the log files will be written
    :type directory: string
    :param prefix: a common prefix for all the logs of this executable
    :type prefix: string

This will write one file for each instance of FSM loaded in the executable, and
will use the prefix, plus the name of the FSM to name the file.

It can be used directly by  creating an instance and passing it as an optional
argument to all the FSMs, or (better) using the :mod:`loader` and its
:func:`logToFile` function. The verbosity can be set with :func:`setVerbosity` function.


Log to Syslog
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Planned**

Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Choosing the logging method::

    from smblib import loader

    l = loader()
    l.setVerbosity(2) # INFO verbosity
    l.logToFile("~/fsmlogs/", "exampleDaemon") # comment this line to log to stdout

    l.load( ... ) # load your FSMs

    l.start()

Using log functions inside the FSM code::

    def mymethod_eval(self):
        self.logE("This is an ERROR level log message!")
        self.logW("This is an WARNING level log message!")
        self.logI("This is an INFO level log message!")
        self.logD("This is an DEBUG level log message!")
