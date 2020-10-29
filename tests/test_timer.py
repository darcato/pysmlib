from smlib import fsmBase, loader
from datetime import datetime
import pytest
from queue import Queue, Empty
import time

# Test timers
# - must wake up the current state
# - must do it after the correct time delta
# - before being set must return expired == True
# - while waiting must return expired == False
# - after expiration must return expired == True
# - (only) during the expiration event must return exipiring == True

class FSM(fsmBase):
    def __init__(self, name, **args):
        super().__init__(name, **args)
        self.events = Queue()
        self.t = datetime.now()
        self.exec_n = 0
        self.gotoState('run')
    
    def register_event(self, name):
        ev = {"name": name}
        ev["t1_expired"] = self.tmrExpired('t1')
        ev["t1_expiring"] = self.tmrExpiring('t1')
        ev["delta"] = datetime.now() - self.t
        ev["exec_n"] = self.exec_n
        self.events.put(ev)

    def run_entry(self):
        self.register_event("before_set")
        self.t = datetime.now()
        self.tmrSet('t1', 0.2)
        self.tmrSet('t1', 0.5) # default reset = True, the active timer is reinitialized
        self.register_event("after_set")
        self.tmrSet('t2', 0.7)
        self.tmrSet('t2', 1, reset=False) # reset = False, the active timer is not changed
        self.exec_n = 0

    def run_eval(self):
        self.register_event("run_eval")
        self.exec_n +=1


# Will be called to produce the argument to test_timer function
# and again after its execution to kill all the FSMs
@pytest.fixture
def loaded_fsm(scope='function'):
    l = loader()
    fsm = l.load(FSM, "test_timer")
    l.start(blocking=False)
    yield fsm
    l.killAll(None, None)

# Test function to check timers expected behaviour
def test_timer(loaded_fsm):
    events = loaded_fsm.events
    
    # before timer t1 is set
    ev = events.get(timeout=1)
    assert ev["name"]=="before_set"
    assert ev["t1_expired"]
    assert not ev["t1_expiring"]

    # after timer t1 is set
    ev = events.get(timeout=1)
    assert ev["name"]=="after_set"
    assert not ev["t1_expired"]
    assert not ev["t1_expiring"]

    # direct first run of run_eval
    ev = events.get(timeout=1)
    assert ev["name"]=="run_eval"
    assert ev["exec_n"]==0
    assert not ev["t1_expired"]
    assert not ev["t1_expiring"]

    # after timer t1 is expired
    ev = events.get(timeout=1)
    assert ev["name"]=="run_eval"
    assert ev["exec_n"]==1
    assert ev["t1_expired"]
    assert ev["t1_expiring"]
    # t1 will expire after 0.5s as it is reset by the second call to tmrSet 
    delta = ev["delta"].seconds + ev["delta"].microseconds/1e6
    assert delta == pytest.approx(0.5, rel=1e-2)

    # after timer t2 is expired
    ev = events.get(timeout=1)
    assert ev["name"]=="run_eval"
    assert ev["exec_n"]==2
    assert ev["t1_expired"]
    assert not ev["t1_expiring"]
    # t2 will expire after 0.7s as the reset on second call is false
    delta = ev["delta"].seconds + ev["delta"].microseconds/1e6
    assert delta == pytest.approx(0.7, rel=1e-2)

    with pytest.raises(Empty):
        ev = events.get(timeout=0.5)
