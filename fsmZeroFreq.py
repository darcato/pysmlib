
from fsm import fsmBase, fsmIOs



class zerFreqFsm(fsmBase):
    def __init__(self, inputs, outputs, statesWithPvs):
        fsmBase.__init__(self, inputs, outputs, statesWithPvs)
        self.freqErr = self.input("freqErr")
        self.enable = self.input("zeroEn")
        self.movn = self.input("m1:motor.MOVN")
        self.position = self.input("m1:motor")
        self.moveRel = self.input("m1:moveRel")
        self.gotoState('init')


    def commonEval(self):
        for io in self._myios:
            pass

    #eval dello stato 'init'        
    def init_eval(self):
        print "init eval"
        self.gotoState('idle')
    
    # facoltativa: questa veiene eseguita una sola volta quando la macchina entra nello stato 1
    def idle_entry(self):
        print "boot-up complete, entering idle..."
        
    # obbligatoria: viene eseguita un numero imprecisato di volte finche' rimane nello stato 1       
    def idle_eval(self):
        print "evaluating 'idle'"
        if enable.val == 1:
            if freqErr.val > 10:
                self.gotoState("outRng_goLow")
            else self.gotoState("inRng_goLows")
    
    def idle_exit(self):
        print "Starting zeroing!"
    
    def outRng_goLow_entry(self):
        freqerr0 = self.input('freqErr').val
        if self.input("m1:motor.MOVN").val == 0         
        self.moveRel.put(100)
        lastmovn = movn


    def outRng_goLow_eval(self):
        print "evaluating outRng_goLow"
        self.gotoState("outRng_gohigh")
    
    def outRng_gohigh_eval(self):
        print "evaluating outRng_gohigh"
        self.gotoState("inRng_golow") 

    def inRng_golow_eval(self):
        print "evaluating inRng_golow"
        self.gotoState("inRng_goHigh")
    
    def inRng_goHigh_eval(self):
        print "evaluating inRng_goHigh"
        self.gotoState("minimize")
    
    def minimize_eval(self):
        print "evaluating minimize"
        self.gotoState("end")
    
    def end_eval(self):
        print "evaluating end"
        self.gotoState("error")
    
    def error_eval(self):
        print "evaluating error"
        self.gotoState("idle")            
        
        
inputs = fsmIOs()
outputs = fsmOutputs()

statesWithPvs = {
"init" : [],
"idle" : ["zeroEn"],
"outRng_goLow" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"outRng_gohigh" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"inRng_golow" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"inRng_goHigh" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"minimize" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"end" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"],
"error" : ["zeroEn","m1:motor", "freqErr", "m1:motor.MOVN", "m1:moveRel"]
}



f = zerFreqFsm(inputs, outputs, statesWithPvs)

f.eval_forever()        
