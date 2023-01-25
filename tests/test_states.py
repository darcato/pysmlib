'''Test FSM states execution with args'''

from smlib import fsmBase, loader
import pytest
import time

class FSM(fsmBase):
    def __init__(self, name, **args):
        super().__init__(name, **args)
        self.counter = []
        self.gotoState("idle")

    def idle_entry(self):
        self.counter.append(0)

    def idle_eval(self):
        self.counter.append(1)

    def only_args_entry(self, num):
        self.counter.append(num-1)

    def only_args_eval(self, num):
        self.counter.append(num)
        self.gotoState("idle")

    def only_args_exit(self, num):
        self.counter.append(num+1)

    def third_entry(self, num):
        self.counter.append(num-1)

    def only_kwargs_entry(self, num=100):
        self.counter.append(num-1)

    def only_kwargs_eval(self, num=100):
        self.counter.append(num)
        self.gotoState("idle")

    def only_kwargs_exit(self, num=100):
        self.counter.append(num+1)

    def args_and_kwargs_entry(self, num, num2=-100):
        self.counter.append(num-1)
        self.counter.append(num2-1)

    def args_and_kwargs_eval(self, num, num2=-100):
        self.counter.append(num)
        self.counter.append(num2)
        self.gotoState("idle")

    def args_and_kwargs_exit(self, num, num2=-100):
        self.counter.append(num+1)
        self.counter.append(num2+1)


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



def test_args(loaded_fsm):
    '''Test gotoState with args'''
    assert loaded_fsm.counter == [0, 1]
    loaded_fsm.gotoState("only_args", 10)
    loaded_fsm.trigger()
    time.sleep(0.1)
    assert loaded_fsm.counter == [0, 1, 9, 10, 11, 0, 1]

def test_kwargs(loaded_fsm):
    '''Test gotoState with kwargs'''
    loaded_fsm.counter = []
    loaded_fsm.gotoState("only_kwargs")
    loaded_fsm.trigger()
    time.sleep(0.1)
    assert loaded_fsm.counter == [99, 100, 101, 0, 1]

def test_kwargs_filled(loaded_fsm):
    '''Test gotoState with kwargs with value'''
    loaded_fsm.counter = []
    loaded_fsm.gotoState("only_kwargs", num=50)
    loaded_fsm.trigger()
    time.sleep(0.1)
    assert loaded_fsm.counter == [49, 50, 51, 0, 1]

def test_args_kwargs(loaded_fsm):
    '''Test gotoState with args and kwargs unfilled'''
    loaded_fsm.counter = []
    loaded_fsm.gotoState("args_and_kwargs", 10)
    loaded_fsm.trigger()
    time.sleep(0.1)
    assert loaded_fsm.counter == [9, -101, 10, -100, 11, -99, 0, 1]

def test_args_kwargs_filled(loaded_fsm):
    '''Test gotoState with args and kwargs filled'''
    loaded_fsm.counter = []
    loaded_fsm.gotoState("args_and_kwargs", 10, num2=50)
    loaded_fsm.trigger()
    time.sleep(0.1)
    assert loaded_fsm.counter == [9, 49, 10, 50, 11, 51, 0, 1]
