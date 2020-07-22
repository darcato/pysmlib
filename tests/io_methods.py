#! /usr/bin/python
from smlib import fsmBase, loader

# FSM definition
class io_methods(fsmBase):
    def __init__(self, name, *args, **kwargs):
        super(io_methods, self).__init__(name, **kwargs)

        self.pv = self.connect("CS:al1")
        self.gotoState('run')

    # idle state
    def run_eval(self):
        print("\nEXECUTING")
        print(self.pv.alarmLimits())
        print(self.pv.alarmName())
        print(self.pv.alarm())
        print(self.pv.putComplete())
        print(self.pv.connected())
        print(self.pv.initialized())
        print(self.pv.initializing())
        print(self.pv.disconnecting())
        print(self.pv.connecting())
        print(self.pv.changing())
        print(self.pv.alarmChanging())
        print(self.pv.alarmDecreasing())
        print(self.pv.alarmIncreasing())
        print(self.pv.putCompleting())
        print(self.pv.falling())
        print(self.pv.rising())
        print(self.pv.val())
        print(self.pv.pval())
        print(self.pv.time())
        print(self.pv.status())
        print(self.pv.precision())
        print(self.pv.units())
        print(self.pv.readAccess())
        print(self.pv.writeAccess())
        print(self.pv.enumStrings())
        print(self.pv.displayLimits())
        print(self.pv.controlLimits())
        print(self.pv.maxLen())
        print(self.pv.host())
        print(self.pv.caType())
        print(self.pv.data())


# Main
if __name__ == '__main__':
    # load the fsm
    l = loader()
    l.load(io_methods, "io_methods")

    # start execution
    l.start()
