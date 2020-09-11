from smlib import fsmBase, loader
from datetime import datetime
import time
from pytest import approx
import pytest

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
        self.gotoState('before')

    def before_entry(self):
        self.tmrSet('t1', 0.5)

    def before_eval(self):
        self.t2_expired = self.tmrExpired('t2')
        if self.tmrExpired('t1'):
            self.gotoState('after')

    def after_entry(self):
        self.t = datetime.now()
        self.tmrSet('t2', 1)
        self.tmrSet('t3', 1.5)

    def after_eval(self):
        self.delta = datetime.now() - self.t
        self.t2_expired = self.tmrExpired('t2')
        self.t2_expiring = self.tmrExpiring('t2')

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
    fsm = loaded_fsm
    time.sleep(0.25)

    # before the timer t2 is set
    assert fsm.t2_expired
    time.sleep(0.5)

    # after timer t2 is set
    assert not fsm.t2_expired
    time.sleep(1)

    # after timer t2 is expired
    assert fsm.t2_expired
    assert fsm.t2_expiring
    assert fsm.delta.seconds + fsm.delta.microseconds/1e6 == approx(1, rel=1e-2)
    time.sleep(0.5)

    # after timer t3 is expired
    assert fsm.t2_expired
    assert not fsm.t2_expiring
