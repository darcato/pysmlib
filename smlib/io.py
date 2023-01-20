# -*- coding: utf-8 -*-
'''
Input - Output objects for finite state machines.

@date: March 26, 2018
@authors: Damiano Bortolato, Davide Marcato
@email: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''

import re
from collections import OrderedDict, deque
from statistics import mean, stdev
from math import sqrt
from datetime import datetime
import threading
import epics
from typing import Union, TYPE_CHECKING

# avoid circular import
if TYPE_CHECKING:
    from .fsm import fsmBase


class epicsIO():
    '''Class representing an IO with Epics support for a finite state machine.'''

    def __init__(self, name:str) -> None:
        self._name = name
        self._data = {}  # keep all infos arriving with change callback
        self._conn = False  # keeps all infos arriving with connection callback

        self._attached = set()  # set of finite state machines using this IO
        self._pv = epics.PV(name, callback=self.chgcb, connection_callback=self.concb, auto_monitor=True)
        self._cond = threading.Condition()

    def ioname(self) -> str:
        '''Return the name of the PV.'''
        return self._name

    def attach(self, fsm: 'fsmBase') -> None:
        '''
        Attach a finite state machine to this IO.
        When a FSM is attached to an IO, it will be triggered when the IO changes.
        '''
        self._attached.add(fsm)

    def isAttached(self, fsm: 'fsmBase') -> bool:
        '''Return True if the finite state machine is attached to this IO.'''
        return fsm in self._attached

    def lock(self) -> None:
        '''Obtain exclusive access on IO.'''
        self._cond.acquire()

    def unlock(self) -> None:
        '''Release exclusive access on IO.'''
        self._cond.release()

    def concb(self, **args) -> None:
        '''Callback called on connections and disconnections.'''
        self.lock()
        self._conn = args.get('conn', False)
        self._data = {}  # not to keep old values after disconnection
        self.trigger("conn", args)
        self.unlock()

    def chgcb(self, **args) -> None:
        '''Callback called on value changes, or initial value after connection.'''
        self.lock()
        self._data = args
        self.trigger("change", args)
        self.unlock()

    def putcb(self, **args) -> None:
        '''Callback called when a put() and relative PV processing has completed.'''
        if 'fsm' in args:
            args['fsm'].trigger(iobj=self, inputname=self._name, reason="putcomp")

    def trigger(self, cbname: str, cbdata: dict) -> None:
        '''
        Wakes up all the finite state machines attached to this IO.
        The finite state machines will be triggered with the given callback name and data.
        '''
        for fsm in self._attached:
            fsm.trigger(iobj=self, inputname=self._name, reason=cbname, cbdata=cbdata)

    def put(self, value, caller_fsm: 'fsmBase') -> bool:
        '''
        Put a value to the PV without wait for the PV processing to complete.
        Returns False if the put() fails to start, may still fail later.
        '''
        # cbdata contains the fsm obj to wake up when putCompleted
        cbdata = {"fsm": caller_fsm}
        try:
            self._pv.put(value, callback=self.putcb, use_complete=True, callback_data=cbdata)
        except Exception as e:
            caller_fsm.logE("FAILED putting to pv %s  -- exception: %s" % (self._name, str(e)))
            return False
        return True

    def putComplete(self) -> bool:
        '''Return True if the most recent put() has completed.'''
        return self._pv.put_complete

    def data(self) -> dict:
        '''Return the data dictionary of the PV.'''
        return self._data

    def connected(self) -> bool:
        '''Return True if the PV is connected.'''
        return self._conn


class fsmIOs():
    '''Class representing a list of epicsIO objects.'''

    def __init__(self) -> None:
        self._ios = {}

    def get(self, name: str, fsm: 'fsmBase', **args) -> epicsIO:
        '''Returns the epicsIO object for the given name and attaches it to the given fsm.'''
        
        # first time this input was requested: we create and attach it
        if name not in self._ios:
            self._ios[name] = epicsIO(name)

        # input already created: if not already attached to the fsm, trigger some 
        # fake events to init fsm
        if not self._ios[name].isAttached(fsm):
            io = self._ios[name]
            io.lock()
            fsm.trigger(iobj=io, inputname=name, reason="conn", cbdata={'conn': io.connected(), 'pvname': name})
            if io.data():
                fsm.trigger(iobj=io, inputname=name, reason="change", cbdata=io.data())
            io.attach(fsm)
            io.unlock()

        fsm.logI("Connecting to PV: {:s}".format(name))
        return self._ios[name]

    def getFsmIO(self, fsm: 'fsmBase') -> dict:
        '''Returns a dictionary of all the epicsIO objects attached to the given fsm.'''
        ret = {}
        for io in self._ios.values():
            if io.isAttached(fsm):
                ret[io.ioname()] = io
        return ret

    def getAll(self) -> list:
        '''Returns a list of all the epicsIO objects.'''
        return self._ios.values()


class mappedIOs(fsmIOs):
    '''
    Performs the conversion from procedure internal namings of the inputs
    and real pv names, base on naming convention and a map
    '''
    
    def __init__(self, mapFile) -> None:
        super(mappedIOs, self).__init__()
        # converts the internal name to the ending of the pv name

        file = open(mapFile, "r")
        lines = file.readlines()
        file.close()

        self._map = {}
        replaces = {}  # a dict with macro substitutions
        pattern = OrderedDict()
        strgen = ""
        for line in lines:
            if not line.startswith("#"):
                line_uncomment = line.split("#")[0].strip()
                if line_uncomment.startswith(">"):
                    el = line_uncomment[1:].split("=")
                    if len(el) == 2:
                        cmd = el[0].strip().replace("\"", "")
                        expression = el[1].strip().replace("\"", "")
                        if cmd == "pattern":  # keywords of the config file
                            pattern = OrderedDict()  # will contain the naming convention elements, with each its format
                            strgen = ""  # will contain the whole string formats
                            m = re.match(r" *\((.*)\) *\((.*)\) *", expression)
                            if m:
                                strgen = m.group(1).strip().replace(" ", "").replace("\"", "")  # first part between {} = string definition
                                strelm = re.findall(r"[^{}]*{([^{}]*)}[^{}]*", strgen)  # parse all the single parts
                                patterns = m.group(2).split(",")  # second part between {} = naming convention elements
                                if not strelm or len(strelm) != len(patterns):
                                    raise ValueError("inputMap ERROR, line {}: Failed to parse pattern elements".format(lines.index(line)))
                                for k, kpattern in enumerate(patterns):
                                    p = kpattern.strip().replace(" ", "").replace("\"", "")
                                    if p != "":
                                        if p not in pattern:
                                            pattern[p] = strelm[k]  # populate pattern
                                        else:
                                            raise ValueError("inputMap ERROR, line {}: Redeclaration of pattern element".format(lines.index(line)))
                                if len(pattern) == 0:
                                    raise ValueError("inputMap ERROR, line {}: Pattern empty")
                            else:
                                raise ValueError("inputMap ERROR, line {}: Pattern syntax error".format(lines.index(line)))
                        else:  # macro definitions
                            replaces[el[0].strip().replace("\"", "").upper()] = el[1].strip().replace("\"", "")
                    elif len(el) > 2:
                        raise ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                elif len(line_uncomment) > 3:  # input definition
                    if len(pattern) != 0 and len(strgen) != 0:  # if a pattern has already been defined
                        el = line_uncomment.split("=")
                        if len(el) == 2:  # if there is an assignation
                            key = el[0].strip().replace("\"", "")  # input name inside fsm
                            values = el[1].split(",")  # info to create pv name elements
                            if len(values) != len(pattern):  # must respect the pattern
                                raise ValueError("inputMap ERROR, line {}: Pattern lenght differs from input declaration".format(lines.index(line)))
                            cmap = OrderedDict()  # map of this input: for each element of pattern there is a value
                            for k in range(len(pattern)):
                                candidate = values[k].strip().replace("\"", "")  # parse from file
                                m = re.match(r" *\$\((.*)\) *", candidate)  # $(MACRO)
                                if m:  # if this is a macro to be replaced
                                    candidate = m.group(1)  # get the macro name
                                    if candidate.upper() in replaces:  # if there is a replacement for the macro in replaces
                                        candidate = replaces[candidate.upper()]  # use the replacement
                                    else:
                                        raise ValueError("inputMap ERROR, line {}: Cannot find macro substitutions for: {}".format(lines.index(line), candidate))
                                cmap[list(pattern.items())[k]] = candidate  # the map of this input has a tuple as key (pattern, strelm) and the parsed candidate as value
                            self._map[key] = (cmap, strgen)  # add the current map (of this input) and the whole strgen to the general map (all inputs)
                        else:
                            ValueError("inputMap ERROR, line {}: Multiple or no assignations in line".format(lines.index(line)))
                    else:
                        raise ValueError("inputMap ERROR, line {}: Declaring an input without first defining a pattern!".format(lines.index(line)))

        # inverse map, to perform back naming transformation
        #self.inv_map = {v: k for k, v in self._map.items()}

    # call parent method to connect pvs with complete names
    # reads from calling fsm the targets and creates base pv name with those infos
    def get(self, name: str, fsm: 'fsmBase', **args) -> epicsIO:
        cmap, strgen = self._map[name]

        substitutions = ()  # a tuple containing the parts of pv name in order
        cstrgen = strgen  # copy the string containing the format of each part
        for pattern, v in cmap.items():
            m = re.match(r" *<(.*)> *", v)  # these are parameters to be passed runtime
            if m:
                v = m.group(1)
                if v in args and args[v] is not None:
                    v = args[v]  # get the value from args
                else:
                    raise ValueError("Cannot find the arg: %s in the input creation, as required by input map" % v)
            keydef = pattern[1]
            if keydef.endswith("d"):  # if we are dealing with an int value, let's format it now and then use it as a string
                if v != "":  # this is done so that if we get a number as string doesn't crash
                    v = ("{"+keydef+"}").format(int(v))  # now the number is a string with the correct format
                cstrgen = cstrgen.replace(keydef, ":s", 1)  # so we change the expected format to %s (replace the first occurence, going from first to last)
            elif keydef == ":c":  # this is a char, let's convert it to a string of lenght 1
                v = ("{:.1s}").format(str(v))
                cstrgen = cstrgen.replace(keydef, ":s", 1)
            substitutions += (v,)  # add the updated v to the tuple pv name parts

        pvname = cstrgen.format(*substitutions)  # actually compose pv name
        return super(mappedIOs, self).get(pvname, fsm, **args)

    # return a dictionary with the orinal (before mapping) names of the ios and ios objs of one fsm
    # def getFsmIO(self, fsm):
    #    iosDict = super(lnlPVs, self).getFsmIO(fsm)
    #    pvsDict = {}
    #    for key, value in iosDict.iteritems():
    #        pvsDict[self.inv_map[key]] = value
    #    return iosDict


class fsmIO():
    '''
    An io which changes only between evaluation of the fsm, due to progressive effect of the event 
    queque it reflects the changes of an fsmIO, one change per cycle
    it implements flags to detect changes, edges, connections and disconnections
    there should be a mirror of the same fsmIO for each fsm, in order to use flags indipendently
    '''

    def __init__(self, fsm: 'fsmBase', io: epicsIO) -> None:
        self._fsm = fsm

        self._name = None
        self._value = None  # pv value
        self._sevr = None
        self._pval = None  # pv previous value
        self._psevr = None
        self._timestamp = 0  # value timestamp
        self._currcb = None  # current callback
        self._putComplete = True  # keep track of put completement

        self._reflectedIO = io  # the io to mirror here
        self._name = io.ioname()
        self._conn = False  # pv connected or not
        self._data = {}  # whole pv data
        self.setBufSize(0)

    def setBufSize(self, s: int) -> None:
        '''
        Set the size of the circular buffer for the valAvg and valStd methods.
        '''
        if s == 0:
            self._cbufVal = None
            self._cbufTime = None
        elif self._cbufVal is not None:
            # new buffer with old data and new maxlen
            self._cbufVal = deque(self._cbufVal, maxlen=s)
            self._cbufTime = deque(self._cbufTime, maxlen=s)
        else:
            self._cbufVal = deque(maxlen=s)
            self._cbufTime = deque(maxlen=s)

    def update(self, reason: str, cbdata: dict) -> None:
        '''
        Update this io with the new data from the callback.
        '''
        if reason == 'change':
            self._currcb = reason
            self._data = cbdata
            self._pval = self._value
            self._psevr = self._sevr
            ptime = self._timestamp
            self._value = self._data.get('value', None)
            self._sevr = self._data.get('severity', None)
            self._timestamp = self._data.get('timestamp', 0)
            if self._value is not None and self._cbufVal is not None:
                self._cbufVal.append(self._value)
                # delta in seconds [float] -> microsecond precision
                # how much previous value lasted
                self._cbufTime.append(self._timestamp-ptime)

        elif reason == 'conn':
            self._currcb = reason
            self._conn = cbdata.get('conn', False)
            # on connection or disconnection reset all previous values of the input
            # in order not to access old values after disconnections
            self._pval = None
            self._psevr = None
            self._value = None
            self._sevr = None
            self._data = {}

        # if a put complete callback arrives, the flag must be set true only if
        # the callback was called due to a put made by this object
        elif reason == 'putcomp':
            self._currcb = reason
            self._putComplete = True
        else:
            self._currcb = ""  # a callback which does not modify this input (eg: putcb for other io)

    def reset(self) -> None:
        '''When the state is changed, the current callback is reset'''
        self._currcb = ""

    def ioname(self) -> str:
        '''Return the name of the io'''
        return self._name

    def put(self, value) -> bool:
        '''Write a value to the io'''
        self._putComplete = False
        return self._reflectedIO.put(value, self._fsm)

    # ----- METHODS THAT CATCH CHANGE ONLY if CHECKED WHEN TRIGGERED BY THE SAME CHANGE ------
    # ----- They return True if the fsm was woken up by this change in this cycle

    def putCompleting(self) -> bool:
        '''The current event is a put complete callback of this IO'''
        return self._currcb == 'putcomp'

    def rising(self) -> bool:
        '''The current event increases the value of this IO'''
        return self._currcb == 'change' and self._pval is not None and self._value > self._pval

    def falling(self) -> bool:
        '''The current event decreases the value of this IO'''
        return self._currcb == 'change' and self._pval is not None and self._value < self._pval

    def alarmIncreasing(self) -> bool:
        '''The current event increases the alarm value of this IO'''
        return self._currcb == 'change' and self._psevr is not None and abs(self._sevr) > abs(self._psevr)

    def alarmDecreasing(self) -> bool:
        '''The current event decreases the alarm value of this IO'''
        return self._currcb == 'change' and self._psevr is not None and abs(self._sevr) < abs(self._psevr)

    def alarmChanging(self) -> bool:
        '''The current event changes the alarm value of this IO'''
        return self._currcb == 'change' and self._psevr is not None and self._sevr != self._psevr

    def changing(self) -> bool:
        '''The current event changes the value of this IO'''
        return self._currcb == 'change' and self._pval is not None

    def disconnecting(self) -> bool:
        '''The current event disconnects this IO'''
        return self._currcb == 'conn' and not self._conn

    def connecting(self) -> bool:
        '''The current event connects this IO'''
        return self._currcb == 'conn' and self._conn

    def initializing(self) -> bool:
        '''The current event brings the first value to this IO after connection'''
        return self._currcb == 'change' and self._pval is None

    # ------METHODS THAT KEEP VAlUE BETWEEN TRIGGERS------

    def putComplete(self) -> bool:
        '''The execution of the last `put` command on this IO has been completed'''
        return self._putComplete

    def initialized(self) -> bool:
        '''This IO has received the first value after connection'''
        return self._conn and self._value is not None

    def connected(self) -> bool:
        '''This IO is connected'''
        return self._conn

    def alarm(self) -> int:
        '''The alarm level of this IO'''
        return self._sevr

    def alarmName(self, short=False) -> str:
        '''The alarm level string of this IO'''
        alarm_levels = {-2: "UNDER THRESHOLD MAJOR ALARM",
                        -1: "UNDER THRESHOLD MINOR ALARM",
                         0: "NO ALARM",
                         1: "OVER THRESHOLD MINOR ALARM",
                         2: "OVER THRESHOLD MAJOR ALARM"}
        if short:
            alarm_levels = {k: " ".join(v.split(' ')[-2:]) for k, v in alarm_levels.items()}
        return alarm_levels.get(self._sevr, 'UNKNOWN ALARM')

    def alarmLimits(self) -> tuple:
        '''The alarm thresholds of this IO'''
        lolo = self._data.get('lower_alarm_limit', None)
        low = self._data.get('lower_warning_limit', None)
        high = self._data.get('upper_warning_limit', None)
        hihi = self._data.get('upper_alarm_limit', None)
        return (lolo, low, high, hihi)

    def val(self, as_string=False) -> Union[float, str]:
        '''Current value of this IO'''
        if as_string:
            return self._data.get('char_value', str(self._value))
        return self._value

    def valAvg(self, timeWeight=False) -> float:
        '''
        Current average value of this IO.
        Use `setBufSize` to set the size of the circular buffer for the average.
        If timeWeight is True, the average is weighted by the time passed at each value.
        '''
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return self._value

        if timeWeight:
            times = list(self._cbufTime)[1:].append(datetime.now().timestamp()-self._timestamp)
            vt = [v * t for v, t in zip(self._cbufVal, times)]
            return sum(vt)/sum(times)

        return mean(self._cbufVal)

    def valStd(self, timeWeight=False) -> float:
        '''
        Current standard deviation of this IO.
        Use `setBufSize` to set the size of the circular buffer for the calculation.
        If timeWeight is True, the standard deviation is weighted by the time passed at each value.
        '''
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return 0

        # https://en.wikipedia.org/wiki/Weighted_arithmetic_mean#Weighted_sample_variance
        # https://www.itl.nist.gov/div898/software/dataplot/refman2/ch2/weightsd.pdf
        if timeWeight:
            m = self.valAvg(timeWeight=True)
            times = list(self._cbufTime)[1:].append(datetime.now().timestamp()-self._timestamp)
            wdiff = [t*((v-m)*(v-m)) for v, t in zip(self._cbufVal, times)]
            n = len(times)
            return sqrt(sum(wdiff)/((n-1)*sum(times)/n))

        return stdev(self._cbufVal)

    def valTrend(self, k=1) -> int:
        '''Return the trend of this IO [0 = flat, 1 = increasing, -1 = decreasing]'''
        if self._cbufVal is None or len(self._cbufVal) < 2:
            return 0
        s = stdev(self._cbufVal)
        d = self._cbufVal[-1] - self._cbufVal[0]
        if d > k*s:
            return 1
        if d < -k*s:
            return -1
        return 0

    def pval(self) -> float:
        '''Previous value of this IO'''
        return self._pval

    def time(self) -> datetime:
        '''Timestamp of the last value of this IO'''
        return datetime.fromtimestamp(self._timestamp)

    def status(self) -> int:
        '''The status of the PV (1 for OK)'''
        return self._data.get('status', None)

    def precision(self) -> int:
        '''The precision of the PV (PREC)'''
        return self._data.get('precision', None)

    def units(self) -> str:
        '''The units of the PV (EGU)'''
        return self._data.get('units', None)

    def readAccess(self) -> bool:
        '''The read access of the PV'''
        return self._data.get('read_access', None)

    def writeAccess(self) -> bool:
        '''The write access of the PV'''
        return self._data.get('write_access', None)

    def enumStrings(self) -> list:
        '''Possible string values of enum PV'''
        return self._data.get('enum_strs', None)
    
    def displayLimits(self) -> tuple:
        '''The display limits of the PV (LOPR, HOPR)'''
        l = self._data.get('lower_disp_limit', None)
        u = self._data.get('upper_disp_limit', None)
        return (l, u)

    def controlLimits(self) -> tuple:
        '''The control limits of the PV (DRVL, DRVH)'''
        l = self._data.get('lower_ctrl_limit', None)
        u = self._data.get('upper_ctrl_limit', None)
        return (l, u)

    def maxLen(self) -> int:
        '''The maximum length of the waveform PV (NELM)'''
        return self._data.get('nelm', None)

    def host(self) -> str:
        '''The host of the IOC publishing this PV (IP:port)'''
        return self._data.get('host', None)

    def caType(self):
        '''The CA type of the PV'''
        return self._data.get('type', None)

    def data(self, key=None):
        '''Return one element from pv data, chosen by key, or all data'''
        if key is not None:
            return self._data.get(key, None)
        return self._data
