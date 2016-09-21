#! /usr/bin/python

from fsm import fsmBase, fsmIOs


class zeroFreqFsm(fsmBase):
    def __init__(self, name, **args):
        fsmBase.__init__(self, name, statesWithPvs, **args)
        self.freqErr = self.input("freqErr")
        self.enable = self.input("zeroEn")
        self.movn = self.input("m1:motor.MOVN")
        self.moveRel = self.input("m1:moveRel")
        self.limitSwitch1 = self.input("m1:motor.HLS")
        self.limitSwitch2 = self.input("m1:motor.LLS")
        self.bigStep = self.input("m1:stepFast")
        self.smallStep = self.input("m1:stepSlow")
        self.progress = 0  #to report progress of the procedure [0-100]
        self.gotoState('init')

        #info to be passed to fsm
        self.maxFreqDelta = 100;
        self.microstep = 64
        self.maxStepsDelta = self.maxFreqDelta*2*self.microstep  #todo: smallstep
        self.midThrs = 250
        self.highThrs = 10e3

        #auxiliary variables
        self.lastmovn = self.movn.val
        self.freqErr0 = self.freqErr.val
        self.stepsDone = 0
        self.foundDirection = 0

    #check all connections useful to the current state
    def commonEval(self):
        if self.enable.conn and self.enable.val==0:
            self.gotoState("end") 
        for io in self._cursens:
            if not self._cursens[io].conn:
                self.gotoState("error")
                self.logW(io + " not connected")

    #write current state name, current operation and progress to pv
    def commonExit(self):
        self.progress += 1 #TODO
        self.reportState = self._nextstatename
       
    def init_eval(self):
        self.gotoState('idle')
        
    def idle_eval(self):
        if self.enable.val == 1:
            if self.freqErr.val <= 1:
                self.gotoState("end")
            elif 1<self.freqErr.val<=self.midThrs:
                print "freq err is %f" % self.freqErr.val
                self.gotoState("badRange")
            elif self.midThrs<self.freqErr.val<self.highThrs:
                self.gotoState("inRange")
            else:
                self.gotoState("outRange")

    #move down of 1000 steps to exit badRange
    def badRange_entry(self):
        if self.movn.val == 0:       
            self.moveRel.put(-100 * self.microstep)  #it was 1000
        self.lastmovn = self.movn.val

    #check if successfully exited the bad range when end of movement
    def badRange_eval(self):
        self.commonEval()
        if self.movn.val < self.lastmovn:
            if self.midThrs<self.freqErr.val<self.highThrs:
                self.gotoState("inRange")
            else:
                self.gotoState("error")

    #move down and save initial freqErr
    def inRange_entry(self):
        self.freqErr0 = self.freqErr.val
        if self.movn.val == 0:
            numSteps = self.bigStep.val if self.freqErr.val>self.midThrs else self.smallStep.val
            self.moveRel.put(-numSteps)
            self.stepsDone = numSteps
        self.lastmovn = self.movn.val

    #move until i exit the delta, where freq is not correlable to movement
    def inRange_eval(self):
        self.commonEval()
        if self.movn.val < self.lastmovn:
            if abs(self.freqErr.val-self.freqErr0)>self.maxFreqDelta*1.1:  #out of delta i assume the freqerr is safe
                self.gotoState("minimize")
                self.foundDirection = -1 if self.freqErr.val < self.freqErr0 else 1
            elif self.freqErr.val >= self.highThrs or self.limitSwitch1.val or self.limitSwitch2.val:  #did not surpassed delta
                self.gotoState("tryUp")
            elif self.stepsDone > self.maxStepsDelta*1.5:  #stall
                self.gotoState("error")
            else:
                numSteps = self.bigStep.val if self.freqErr.val>self.midThrs else self.smallStep.val
                self.moveRel.put(-numSteps)
                self.stepsDone = numSteps
        self.lastmovn = self.movn.val

    #move fast until enter the <10k range
    def outRange_entry(self):
        if self.movn.val == 0:
            self.moveRel.put(-self.bigStep.val)
            self.stepsDone = self.bigStep.val
        self.lastmovn = self.movn.val

    #continue moving
    def outRange_eval(self):
        self.commonEval()
        if self.movn.val < self.lastmovn:
            if self.freqErr.val < self.highThrs-self.maxFreqDelta*1.3:   #out of delta and inside 10k
                self.gotoState("minimize")
                self.foundDirection = -1
            elif self.limitSwitch1.val or self.limitSwitch2.val:  #limit switch
                self.gotoState("tryUp")
            elif self.stepsDone > maxSteps*1.1:            #stall
                self.gotoState("error")
            else:                                #continue moving
                self.moveRel.put(-self.bigStep.val)
                self.stepsDone += self.bigStep.val
        self.lastmovn = self.movn.val

    def tryUp_entry(self):
        self.freqErr0 = self.freqErr.val
        if movn.val == 0:
            numSteps = self.bigStep.val if self.freqErr.val>self.midThrs else self.smallStep.val
            self.moveRel.put(numSteps)
            self.stepsDone = numSteps
        self.lastmovn = self.movn.val

    def tryUp_eval(self):
        self.commonEval()
        if self.movn.val < self.lastmovn:
            if abs(self.freqErr.val-self.freqErr0)>self.maxFreqDelta*1.1:
                self.gotoState("minimize")
                self.foundDirection = 1 if self.freqErr.val < self.freqErr0 else -1
            elif self.limitSwitch1.val or self.limitSwitch2.val:
                self.gotoState("error")
            elif self.freqErr0>=highThrs and self.stepsDone>=self.maxSteps*1.1:
                self.gotoState("error")
            elif self.freqErr0<highThrs and self.stepsDone>=self.maxStepsDelta*1.5:
                self.gotoState("error")
            else:
                numSteps = self.bigStep.val if self.freqErr.val>self.midThrs else self.smallStep.val
                self.moveRel.put(numSteps)
                self.stepsDone = numSteps
        self.lastmovn = self.movn.val

    def minimize_entry(self):
        self.freqErr0 = self.freqErr.val
        self.lastmovn = 1

    def minimize_eval(self):
        self.commonEval()
        if self.movn.val < self.lastmovn:
            if self.stepsDone > self.maxStepsDelta and self.freqErr.val>self.freqErr0*1.3:
                self.gotoState("error")
            elif self.freqErr.val > 100:
                #set fast mode
                numSteps = (self.freqErr.val - 50) * self.smallStep.val
                self.moveRel.put(numSteps*self.foundDirection)
            elif freqErr.val > 20:
                #pass to slow mode acquisition
                if self.freqErr0 > 120:
                    self.freqErr0 = 120
                numSteps = (self.freqErr.val - 10) * self.smallStep.val
                self.moveRel.put(numSteps*self.foundDirection)
            elif freqErr.val > 10:
                #be sure to be in slow mode
                if self.freqErr0 > 30:
                    self.freqErr0 = 30
                self.moveRel.put(self.smallStep.val*self.foundDirection)
            elif freqErr > 1:
                #be sure to be in slow mode
                if self.freqErr0 > 15:
                    self.freqErr0 = 15
                self.moveRel.put(self.microstep*self.foundDirection)
            else:
                self.gotoState("end")
        self.lastmovn = self.movn.val
    
    def end_eval(self):
        if self.enable.conn:
            self.enable.put(0);
            self.gotoState("idle")
    
    def error_eval(self):
        if self.enable.conn:
            self.enable.put(0);
            self.gotoState("idle")            

statesWithPvs = {
    "init" : ["zeroEn", "m1:motor.MOVN", "freqErr", "m1:moveRel", "m1:motor.HLS", "m1:motor.LLS", "m1:stepFast", "m1:stepSlow"],
    "idle" : ["zeroEn"],
    "badRange" : ["zeroEn", "m1:motor.MOVN"],
    "inRange" : ["zeroEn", "m1:motor.MOVN"],
    "outRange" : ["zeroEn", "m1:motor.MOVN"],
    "tryUp" : ["zeroEn", "m1:motor.MOVN"],
    "minimize" : ["zeroEn", "m1:motor.MOVN"],
    "end" : ["zeroEn"],
    "error" : ["zeroEn"]
}

if __name__ == '__main__':        
    fsm = zeroFreqFsm('zeroFreq')
    fsm.eval_forever()