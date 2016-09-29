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
        #self.maxFreqDelta = 100;  #max false increment in wrong direction
        self.microstep = 64
        #self.maxStepsDelta = self.maxFreqDelta*3  #todo: smallStep
        self.maxUncertain = 100 #the maximum freq noise in each point -> should become a linear fit
        self.midThrs = 100 + 2.2*125#self.bigStep.val   
        self.highThrs = 10e3 #the max read freq err
        self.maxSteps = 130e3  #total steps between limit swtiches
        self.stepPerSec = 100  #seconds to perform a microstep


        #auxiliary variables
        self.freqErrPrev = self.freqErr.val
        self.stepsDone = 0
        self.foundDirection = 0
        self.freqErrAvg = 0
        self.nSamples = 0
        self.returnState = ""

    #check all connections useful to the current state
    def myEval(self):
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
        #set velocity and accelerations
        self.gotoState('idle')
        
    def idle_entry(self):
        self.foundDirection = -1
        self.stepsDone = 0
        
    def idle_eval(self):
        if self.freqErr.val:
            self.logD('freq erro %.3f' % self.freqErr.val)
        if self.enable.val == 1:
            self.logTimeReset() #reset time of the logger, will print times relative to now
            if self.freqErr.val < 1:
                self.gotoState("end")
            elif 1<self.freqErr.val<=self.midThrs:
                print "freq err is %f" % self.freqErr.val
                self.gotoState("badRange")
            elif self.midThrs<self.freqErr.val<self.highThrs:
                self.gotoState("inRange")
            else:
                self.gotoState("outRange")

    #move down of 1000Hz to exit badRange
    def badRange_entry(self):
        self.logD("moving of 1kHz to exit badrange")
        #will go to a freq range of [1kHz-2midThrs -> 1kHz+midThrs] depending on the starting point & direction
        numSteps = self.smallStep.val * 1000
        self.moveRel.put(self.foundDirection*numSteps) #it was 1000 full steps in old system
        self.tmrSet('moveTimeout', numSteps*self.stepPerSec*1.5)

    #check if successfully exited the bad range when end of movement
    def badRange_eval(self):
        self.myEval()
        if self.limitSwitch1.val or self.limitSwitch2.val:
            self.logE("reached limit switch with low freq err (%.2f), check mountings; aborting.." % self.freqErr.val)
            self.gotoState("error")
        elif self.movn.falling():
            self.returnState = "badRange2"
            self.gotoState("antiBounce")
        elif self.tmrExp("moveTimeout"):
            self.logE("waiting too long for movement to finish")
            self.gotoState("error")    

    def badRange2_eval(self):
        self.myEval()
        if self.midThrs<self.freqErrAvg<self.highThrs:
            self.gotoState("inRange")
        else:
            self.logE("ops: gone out of range or stall: read %.2fHz" % (self.freqErr.val))
            self.gotoState("error")

    def inRange_entry(self):
        self.freqErrPrev = self.freqErr.val
        numSteps = self.bigStep.val
        self.moveRel.put(self.foundDirection*numSteps)
        self.tmrSet("moveTimeout", numSteps/self.stepPerSec*1.5)
        self.escapeLimSwOn = 0
        if self.limitSwitch1.val or self.limitSwitch2.val:
            self.tmrSet("escapeLimSw", 1)
            self.escapeLimSwOn = 1

    def inRange_eval(self):
        self.myEval()
        if self.escapeLimSwOn and tmrExp("escapeLimSw") and (self.limitSwitch1.val or self.limitSwitch2.val):
            if self.foundDirection ==-1:
                self.foundDirection = 1
                self.freqErrPrev = self.freqErr.val
                numSteps = self.bigStep.val
                self.moveRel.put(self.foundDirection*numSteps)
                self.tmrSet("moveTimeout", numSteps/self.stepPerSec*1.5)
                self.tmrSet("escapeLimSw", 1)
                self.escapeLimSwOn = 1
            elif self.foundDirection == 1:
                self.gotoState("error")
                self.logE("could not escape limit switches in any direction")
        elif self.movn.falling():
            self.returnState = "inRange2"
            self.gotoState("antiBounce")
        elif self.tmrExp("moveTimeout") and self.tmrExp("escapeLimSw"):
            self.logE("waiting too long for movement to finish")
            self.gotoState("error")

    def antiBounce_entry(self):
        self.tmrSet("antiBounce", 0.3)

    def antiBounce_eval(self):
        self.myEval()
        if self.tmrExp("antiBounce"):
            self.gotoState("averaging")

    def averaging_entry(self):
        self.freqErrAvg = 0
        self.nSamples = 0
        self.tmrSet("averaging", 0.7)

    def averaging_eval(self):
        self.myEval()
        self.freqErrAvg += self.freqErr.val
        self.nSamples += 1
        if self.nSamples>=3 or self.tmrExp("averaging"):
            self.freqErrAvg /= self.nSamples
            self.gotoState(self.returnState)
            self.logD("read %d samples, with avg value of %.2f" %(self.nSamples, self.freqErrAvg))

    def inRange2_eval(self):
        self.myEval()
        if abs(self.freqErrAvg-self.freqErrPrev)>0.5*self.bigStep.val/self.smallStep.val:  #moved at least 50% of what expected
            self.gotoState("startMinimize")
            if self.freqErrAvg > self.freqErrPrev:
                self.foundDirection = -self.foundDirection
        elif (self.limitSwitch1.val or self.limitSwitch2.val) and self.foundDirection==-1:
            gotoState("inRange")
            self.foundDirection = 1
        elif self.freqErrAvg>=self.highThrs:
            self.gotoState("outRange")
            self.foundDirection = 1
        else: #freq did not change enough
            self.logE("stall detected!")
            self.gotoState("error")

    #move fast until enter the <10k range
    def outRange_entry(self):
        #I need to hit a 20kHz window, try with steps of 6.5kHz (should find at least 3 hit)
        numSteps += self.smallStep.val * 6.5e3
        self.moveRel.put(self.foundDirection*numSteps)
        self.tmrSet('moveTimeout', numSteps/self.stepPerSec*1.5)
        self.escapeLimSwOn = 0
        if self.limitSwitch1.val or self.limitSwitch2.val:
            self.tmrSet("escapeLimSw", 1)
            self.escapeLimSwOn = 1

    #continue moving at 6.5kHz steps until inRange, limit switch or error
    def outRange_eval(self):
        self.myEval()
        if self.escapeLimSwOn and tmrExp("escapeLimSw") and (self.limitSwitch1.val or self.limitSwitch2.val):
            if self.foundDirection ==-1:
                self.foundDirection = 1
                numSteps = self.smallStep.val * 6.5e3
                self.moveRel.put(self.foundDirection*numSteps)
                self.stepsDone += numSteps
                self.tmrSet("moveTimeout", numSteps/self.stepPerSec*1.5)
                self.tmrSet("escapeLimSw", 1)
                self.escapeLimSwOn = 1
            elif self.foundDirection == 1:
                self.gotoState("error")
                self.logE("could not escape limit switches in any direction")
        elif self.movn.falling():
            self.returnState = "outRange2"
            self.gotoState("antiBounce")
        elif self.tmrExp("moveTimeout") and self.tmrExp("escapeLimSw"):
            self.logE("waiting too long for movement to finish")
            self.gotoState("error")

    def outRange2_eval(self):
        self.myEval()
        if self.freqErrAvg < self.highThrs-self.maxUncertain: #inside 10k
            self.gotoState("startMinimize")
        elif (self.limitSwitch1.val or self.limitSwitch2.val) and self.foundDirection==-1:  #first limit switch
            self.foundDirection = 1
            self.logD("changing direction")
            self.gotoState("outRange")
        elif (self.limitSwitch1.val or self.limitSwitch2.val) and self.foundDirection==1:
            self.gotoState("error")
            self.logE("hit limit switches in both directions")
        elif self.stepsDone > self.maxSteps*2.1: #stall
            self.logE("stall detected!")
            self.gotoState("error")
        else: #continue moving
            gotoState("outRange")

    # useful to initialize minimize
    def startMinimize_eval(self):    
        self.stepsDone = 0
        self.freqErrPrev = self.freqErr.val
        self.gotoState("minimize")
        self.logD("initial frequency error is %.3f direction %d ~~~~~~~~~~~~" % (self.freqErrPrev, self.foundDirection))
        self.tmrSet("minimizeTimeout", 120)

    #check status and call move to minimize
    def minimize_eval(self):
        self.myEval()
        self.logD('current freq error %.3f' % self.freqErr.val  )
        self.amount = 0;
        f0 = 100
        f1 = 15
        f2 = 3
        if self.tmrExp("minimizeTimeout"): #minimizeTimeout
            self.gotoState("error")
            self.logE("minimize is taking too long without converging")
        elif self.limitSwitch1.val or self.limitSwitch2.val: #should not find limit switches
            self.gotoState("error")
            self.logE("limit switch toggled while minimizing")
        elif self.stepsDone > self.bigStep.val and abs(self.freqErrAvg-self.freqErrPrev)<=self.stepsDone/self.smallStep.val*0.50: #stall
             self.gotoState("error")
             self.logE("stall detected!")
        elif self.stepsDone > self.bigStep.val and self.freqErr.val>self.freqErrPrev*1.3:  #coming back
            self.logI("ops: coming back after %d steps" %self.stepsDone)
            self.gotoState("error")
        #[100Hz - 10kHz] proportional towards 50Hz
        elif self.freqErrAvg > f0:
            #set fast mode
            self.logD("going towards -> 50")
            self.logD("max frequency error: %.3f" % self.freqErrPrev)      
            numSteps = (self.freqErrAvg - 50) * self.smallStep.val
            self.amount = numSteps*self.foundDirection
            self.gotoState("move")
        #[15Hz - 100Hz] proportional towards 5Hz
        elif self.freqErrAvg > f1:
            #pass to slow mode acquisition
            self.logD("going towards -> 5")
            self.logD("max frequency error: %.3f" % self.freqErrPrev)
            numSteps = (self.freqErrAvg - 5) * self.smallStep.val
            self.amount = numSteps*self.foundDirection
            self.gotoState("move")
        #[3Hz - 15Hz] - smallStep
        elif self.freqErrAvg > f2:
            #be sure to be in slow mode
            self.logD("going towards -> 0 smallStep")
            self.logD("max frequency error: %.3f" % self.freqErrPrev)
            self.amount = self.smallStep.val*self.foundDirection
            self.gotoState("move")
        #[1Hz - 3Hz] - microstep
        elif self.freqErrAvg > 1:
            #be sure to be in slow mode
            self.logD("going towards -> 0 onestep")
            self.logD("max frequency error: %.3f" % self.freqErrPrev)
            self.amount = self.foundDirection
            self.gotoState("move")
        #[0Hz - 1Hz] target reached
        else:
            self.gotoState("end")
    
    #perform movement
    def move_entry(self):
        self.freqErrPrev = self.freqErr.val
        self.moveRel.put(self.amount)
        self.logD("moving of %d steps" % self.amount)
        self.stepsDone += self.amount
        self.tmrSet('moveTimeout', abs(self.amount)/self.stepPerSec*1.5)

    #wait for movement to end and return to minimize
    def move_eval(self):
        self.logD("freqErr: %.2f - movn %d" %(self.freqErr.val, self.movn.val))
        self.myEval()
        if self.movn.falling():
            self.returnState="minimize"
            self.gotoState("antiBounce")
        elif self.tmrExp('moveTimeout'): # self.movn.falling():
            self.logE("waiting too long for movement to finish")
            self.gotoState("error")

    #success
    def end_entry(self):
        self.enable.put(0)
        self.logD("frequency successfully reduced to zero!")
        self.tmrSet('exit',2)

    #wait a timer and return to idle
    def end_eval(self):
        if self.tmrExp('exit'):
            self.gotoState("idle")
    
    #fail
    def error_eval(self):
        self.logD("ERROR: cannot complete frequency zeroing")
        if self.enable.conn:
            self.enable.put(0);
            self.gotoState("idle")            

statesWithPvs = {
    "init" : ["zeroEn", "m1:motor.MOVN", "freqErr", "m1:moveRel", "m1:motor.HLS", "m1:motor.LLS", "m1:stepFast", "m1:stepSlow"],
    "idle" : ["zeroEn"],
    "badRange" : ["zeroEn", "m1:motor.MOVN", "m1:motor.HLS", "m1:motor.LLS"],
    "inRange" : ["zeroEn", "m1:motor.MOVN", "m1:motor.HLS", "m1:motor.LLS"],
    "outRange" : ["zeroEn", "m1:motor.MOVN", "m1:motor.HLS", "m1:motor.LLS"],
    "minimize" : ["zeroEn", "freqErr", "m1:motor.HLS", "m1:motor.LLS"],
    "move" : ["zeroEn", "m1:motor.MOVN", "m1:motor.HLS", "m1:motor.LLS"],
    "end" : ["zeroEn"],
    "error" : ["zeroEn"]
}

if __name__ == '__main__':        
    fsm = zeroFreqFsm('zeroFreq')
    fsm.eval_forever()