import pytest
from smlib import fsmBase, loader, fsmLogger, fsmFileLogger, fsmIOs, mappedIOs
#from pcaspy import SimpleServer
#from pcaspy.tools import ServerThread

def test_setVerbosity():
    #default value 2=info
    assert loader.__verbosity == 2
    assert loader.__logger._level == 2 
    
    # test setting verbosity via number
    loader.setVerbosity(-1)
    assert loader.__logger._level == 0
    assert loader.__verbosity == 0
    loader.setVerbosity(0)
    assert loader.__verbosity == 0
    assert loader.__logger._level == 0
    loader.setVerbosity(1)
    assert loader.__verbosity == 1
    assert loader.__logger._level == 1
    loader.setVerbosity(2)
    assert loader.__verbosity == 2
    assert loader.__logger._level == 2
    loader.setVerbosity(3)
    assert loader.__verbosity == 3
    assert loader.__logger._level == 3
    loader.setVerbosity(4)
    assert loader.__verbosity == 3
    assert loader.__logger._level == 3

    # test setting verbosity via string
    loader.setVerbosity("error")
    assert loader.__verbosity == 0
    assert loader.__logger._level == 0
    loader.setVerbosity("warning")
    assert loader.__verbosity == 1
    assert loader.__logger._level == 1
    loader.setVerbosity("info")
    assert loader.__verbosity == 2
    assert loader.__logger._level == 2
    loader.setVerbosity("debug")
    assert loader.__verbosity == 3
    assert loader.__logger._level == 3
    with pytest.raises(KeyError):
        loader.setVerbosity("otherstring")


def test_logToFile():
    #default value
    assert isinstance(loader.__logger, fsmLogger)

    loader.logToFile("dir", "prefix")
    assert isinstance(loader.__logger, fsmFileLogger)
    assert loader.__logger.dir == "dir"
    assert loader.__logger.prefix == "prefix"
    assert loader.__logger._level == loader.__verbosity


def test_setIoMap():
    #default
    assert isinstance(loader.__ioManager, fsmIOs)

    loader.setIoMap("../examples/config/iomap.txt")
    assert isinstance(loader.__ioManager, mappedIOs)

def test_load():
    #default
    assert len(loader.__fsmsList) == 0

    class fsm_fake(object):
        def __init__(self, name, num, **kwargs):
            self.timerManager = kwargs.get("tmgr", None)
            self.ioManager = kwargs.get("ios", None)
            self.logger = kwargs.get("logger", None)
            self.args = num
        
    loader.load(fsm_fake, "testname", 5)
    assert len(loader.__fsmsList) == 1
    loaded = loader.__fsmsList[0]
    assert isinstance(loaded, fsm_fake)
    assert loaded.timerManager == loader.__timerManager
    assert loaded.ioManager == loader.__ioManager
    assert loaded.logger == loader.__logger
    assert loaded.args == 5