#! /usr/bin/python
from smlib import fsmBase, loader

# FSM definition
class exampleFsm(fsmBase):
    def __init__(self, name, *args, **kwargs):
        super(exampleFsm, self).__init__(name, **kwargs)

        self.counter = self.connect("testcounter")
        self.mirror = self.connect("testmirror")
        self.enable = self.connect("testenable")

        self.gotoState('idle')

    # idle state
    def idle_eval(self):
        if self.enable.rising():
            self.gotoState("mirroring")

    # mirroring state
    def mirroring_eval(self):
        if self.enable.falling():
            self.gotoState("idle")
        elif self.counter.changing():
            readValue = self.counter.val()
            self.mirror.put(readValue)

# Main
if __name__ == '__main__':
    # load the fsm
    l = loader()
    l.load(exampleFsm, "myFirstFsm")

    # start execution
    l.start()
