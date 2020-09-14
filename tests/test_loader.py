import pytest
from smlib import fsmBase, loader, fsmLogger, fsmFileLogger, fsmIOs, mappedIOs

def test_setVerbosity():
    l = loader()

    #default value 2=info
    assert l._verbosity == 2
    assert l._logger._level == 2 
    
    # test setting verbosity via number
    l.setVerbosity(-1)
    assert l._logger._level == 0
    assert l._verbosity == 0
    l.setVerbosity(0)
    assert l._verbosity == 0
    assert l._logger._level == 0
    l.setVerbosity(1)
    assert l._verbosity == 1
    assert l._logger._level == 1
    l.setVerbosity(2)
    assert l._verbosity == 2
    assert l._logger._level == 2
    l.setVerbosity(3)
    assert l._verbosity == 3
    assert l._logger._level == 3
    l.setVerbosity(4)
    assert l._verbosity == 3
    assert l._logger._level == 3

    # test setting verbosity via string
    l.setVerbosity("error")
    assert l._verbosity == 0
    assert l._logger._level == 0
    l.setVerbosity("warning")
    assert l._verbosity == 1
    assert l._logger._level == 1
    l.setVerbosity("info")
    assert l._verbosity == 2
    assert l._logger._level == 2
    l.setVerbosity("debug")
    assert l._verbosity == 3
    assert l._logger._level == 3
    with pytest.raises(KeyError):
        l.setVerbosity("otherstring")


def test_logToFile():
    l=loader()
    
    #default value
    assert isinstance(l._logger, fsmLogger)

    l.logToFile("dir", "prefix")
    assert isinstance(l._logger, fsmFileLogger)
    assert l._logger.dir == "dir"
    assert l._logger.prefix == "prefix"
    assert l._logger._level == l._verbosity


def test_setIoMap():
    l = loader()
    
    #default
    assert isinstance(l._ioManager, fsmIOs)

    l.setIoMap("../examples/config/iomap.txt")
    assert isinstance(l._ioManager, mappedIOs)

def test_load():
    l = loader()
    
    #default
    assert len(l._fsmsList) == 0

    class fsm_fake(object):
        def __init__(self, name, num, **kwargs):
            self.timerManager = kwargs.get("tmgr", None)
            self.ioManager = kwargs.get("ios", None)
            self.logger = kwargs.get("logger", None)
            self.args = num
        
    l.load(fsm_fake, "testname", 5)
    assert len(l._fsmsList) == 1
    loaded = l._fsmsList[0]
    assert isinstance(loaded, fsm_fake)
    assert loaded.timerManager == l._timerManager
    assert loaded.ioManager == l._ioManager
    assert loaded.logger == l._logger
    assert loaded.args == 5