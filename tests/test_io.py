from smlib import fsmBase, loader
import pytest
from queue import Queue, Empty
from pcaspy import SimpleServer, Driver
from pcaspy.tools import ServerThread
import epics

# Test IO
# - Check main methods of epics IO


# Dummy PV driver, just store PV values as set by external puts
class ioDriver(Driver):
    def __init__(self):
        super().__init__()


class FSM(fsmBase):
    def __init__(self, name, **args):
        super().__init__(name, **args)
        self.events = Queue(maxsize=1000)
        self.exec_n = 0

        self.pv1 = self.connect('Ts:pv1')
        #self.pv2 = self.connect('pv2')
        #self.wf = self.connect('wf')

        self.gotoState('idle')

    def register_event(self, name):
        ev = {"name": name}
        ev["pv1_connected"] = self.pv1.connected()
        ev["pv1_connecting"] = self.pv1.connecting()
        ev["pv1_disconnecting"] = self.pv1.disconnecting()
        ev["pv1_initialized"] = self.pv1.initialized()
        ev["pv1_initializing"] = self.pv1.initializing()
        ev["pv1_changing"] = self.pv1.changing()
        ev["awaker"] = self.whoWokeMe()[0]
        ev["reason"] = self.whyWokeMe()
        ev["value"] = self.pv1.val()
        ev["exec_n"] = self.exec_n
        print(ev)
        self.events.put(ev)

    def idle_entry(self):
        self.exec_n = 0
        self.register_event("idle_entry")

    def idle_eval(self):
        self.exec_n += 1
        self.register_event("idle_eval")


# Will be called to produce the argument to test_io function
# and again after its execution to kill all the FSMs
@pytest.fixture(scope='module')
def loaded_fsm():
    l = loader()
    fsm = l.load(FSM, "test_io")
    l.start(blocking=False)

    yield fsm
    # After tests have completed or failed
    l.killAll(None, None)


# Will be called to produce the argument to test_io function
# and again after its execution to kill all the FSMs
@pytest.fixture
def pv_server(scope='function'):
    prefix = 'Ts:'
    pvdb = {
        'pv1': {
            'value': 0,
            'hihi': 10,
            'high':  5,
            'low': -5,
            'lolo': -10
        },
        'pv2': {},
        'wf': {
            'type': 'char',
            'count': 300,
            'value': 'some initial message. but it can become very long.'
        }
    }

    server = SimpleServer()
    server.createPV(prefix, pvdb)
    driver = ioDriver()
    server_thread = ServerThread(server)
    server_thread.start()

    yield server_thread

    # After tests have completed or faileds
    server_thread.stop()

# Test function to check timers expected behaviour
def test_connection(loaded_fsm, pv_server):
    events = loaded_fsm.events
    pv1 = epics.PV('Ts:pv1')
    #pv2 = epics.PV('pv2')
    #wf = epics.PV('wf')

    # first automatic run of idle_entry()
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_entry"
    assert ev["awaker"] is None
    assert not ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert not ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] is None
    assert ev["exec_n"] == 0

    # first automatic run of idle_eval()
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is None
    assert not ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert not ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] is None
    assert ev["exec_n"] == 1

    # fake connection event to initialize fsm
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is not None
    assert not ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert not ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] is None
    assert ev["exec_n"] == 2

    # connection event
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is not None
    assert ev["pv1_connected"]
    assert ev["pv1_connecting"]
    assert not ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] is None
    assert ev["exec_n"] == 3

    # first change event to initialize the IO
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is not None
    assert ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert ev["pv1_initialized"]
    assert ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] == 0
    assert ev["exec_n"] == 4

    # change event
    pv1.put(3)
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is not None
    assert ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert ev["pv1_changing"]
    assert ev["value"] == 3
    assert ev["exec_n"] == 5


def test_disconnection(loaded_fsm):
    events = loaded_fsm.events

    # Disconnection event
    ev = events.get(timeout=1)
    assert ev["name"] == "idle_eval"
    assert ev["awaker"] is not None
    assert not ev["pv1_connected"]
    assert not ev["pv1_connecting"]
    assert ev["pv1_disconnecting"]
    assert not ev["pv1_initialized"]
    assert not ev["pv1_initializing"]
    assert not ev["pv1_changing"]
    assert ev["value"] is None
    assert ev["exec_n"] == 6

    # No more events
    with pytest.raises(Empty):
        ev = events.get(timeout=0.5)
