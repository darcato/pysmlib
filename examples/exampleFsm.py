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
        if self.enable.rising() == 0:
            self.gotoState("mirroring")

    # mirroring state
    def mirroring_eval(self):
        if self.enable.falling() == 0:
            self.gotoState("idle")
        elif self.mirror.changing():
            readValue = self.mirror.val()
            self.mirror.put(readValue)

## -------------------
# load each fsm
## -------------------
loader.load(exampleFsm, "myFirstFsm")

## -------------------
# start execution
## -------------------
loader.start()