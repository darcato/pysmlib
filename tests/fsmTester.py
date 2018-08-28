# -*- coding: utf-8 -*-
'''
Created on 15 set 2016
@author: damiano.bortolato@lnl.infn.it - davide.marcato@lnl.infn.it
'''


from smlib import fsmBase, fsmLogger, fsmTimers
from smlib.fsm import fsmTimer
from smlib.fsm import fsmIO
from time import sleep
import unittest
import StringIO
import sys


class TestFsmLogger(unittest.TestCase):
    def setUp(self):
        self._oldstdout = sys.stdout
        sys.stdout = StringIO.StringIO()
        self.uut = fsmLogger()
#        self.longMessage = True


    def test_loglevel(self):
        
        for ovlevel in [None, 0, 1, 2, 3]:
            for clevel in range(4):
                self.uut._level = clevel
                for mlevel in range(4):
                    self.uut.log('test', mlevel, 'testmsg', ovlevel)                
                    outm = sys.stdout.getvalue()
                    sys.stdout = StringIO.StringIO()
                    elevel = clevel if ovlevel is None else ovlevel    
                    if mlevel <= elevel:                
                        self.assertNotEqual(outm, '', msg='Got any output with message level %d and logger level %d' % (mlevel, clevel))
                        self.assertEqual(outm[-8:-1], 'testmsg', msg='Wrong response from UUT: \'%s\'' % outm.encode('string-escape'))
                        self.assertEqual(outm[11], fsmLogger.levstr[mlevel])                
                    else:
                        self.assertEqual(outm, '', msg='Unexpected output from UUT: \'%s\'. message level is %d, logger level is %d' % (outm.encode('string-escape'), mlevel, clevel))
                    

    def tearDown(self):
        sys.stdout = self._oldstdout


class TestFsmTimer(unittest.TestCase):

    class fsm_fake():
        def __init__(self):
            self.args=None
        
        def trigger(self, **args):
            #print "expire %s" % args['timername']
            self.args = args            

    def setUp(self):
        self.fsm = TestFsmTimer.fsm_fake()
        self.uut = fsmTimer(self.fsm, 'test_timer')
        self.uut1 = fsmTimer(self.fsm, 'test_timer1')
        self.timers = fsmTimers()
        self.timers.start()

    def tearDown(self):
        self.timers.kill()

    def checktimer(self, tmrname, uut):
        self.assertIsNotNone(self.fsm.args)
        self.assertIn('tmrobj', self.fsm.args)
        self.assertIn('timername', self.fsm.args)
        self.assertIn('reason', self.fsm.args)
        self.assertEqual(uut, self.fsm.args['tmrobj'])
        self.assertEqual(self.fsm.args['timername'], tmrname)
        self.assertEqual(self.fsm.args['reason'], 'expired')

    def test_timer(self):
        self.timers.set(self.uut, 2.0)
        sleep(1.95)
        self.assertIsNone(self.fsm.args)    
        sleep(0.1)
        self.checktimer('test_timer', self.uut) 

    def test_timer_reset(self):
        self.timers.set(self.uut, 2.0)
        sleep(1.0)
        self.assertIsNone(self.fsm.args)
        self.timers.set(self.uut, 2.0)
        sleep(1.95)
        self.assertIsNone(self.fsm.args)    
        sleep(0.1)
        self.checktimer('test_timer', self.uut) 

    def test_2timers(self):
        self.timers.set(self.uut, 2.0)
        self.timers.set(self.uut1, 3.0)
        sleep(1.95)
        self.assertIsNone(self.fsm.args)    
        sleep(0.1)
        self.checktimer('test_timer', self.uut) 
        sleep(1.0)
        self.checktimer('test_timer1', self.uut1) 

    def test_2timers_reversed(self):
        self.timers.set(self.uut1, 3.0)
        self.timers.set(self.uut, 2.0)
        sleep(1.95)
        self.assertIsNone(self.fsm.args)    
        sleep(0.1)
        self.checktimer('test_timer', self.uut) 
        sleep(1.0)
        self.checktimer('test_timer1', self.uut1) 

    def test_2timers_reset(self):
        self.timers.set(self.uut, 2.0)
        self.timers.set(self.uut1, 3.0)
        sleep(1)
        self.timers.set(self.uut, 3.0)
        sleep(1.95)
        self.assertIsNone(self.fsm.args)    
        sleep(0.1)
        self.checktimer('test_timer1', self.uut1) 
        sleep(1.0)
        self.checktimer('test_timer', self.uut) 



class TestFsmIO(unittest.TestCase):

    class fsm_fake():
        def __init__(self):
            self.evts = []
        
        def trigger(self, **args):
            self.evts.append(args)

    def setUp(self):
        self.fsm = TestFsmIO.fsm_fake()

    def test_conn_connected(self):
        io = fsmIO("testinput")
        sleep(0.1)
        io.attach(self.fsm)
        self.assertGreater(len(self.fsm.evts), 0)
        
        evcnt = 0
        ev = self.fsm.evts[evcnt]
        self.assertIn('reason', ev)
        self.assertEqual(ev['reason'], 'conn')
        self.assertIn('cbdata', ev)
        self.assertIn('conn', ev['cbdata'])
        self.assertTrue(ev['cbdata']['conn'])

    def test_conn_disconnected(self):
        io = fsmIO("notexists")
        sleep(0.1)
        io.attach(self.fsm)
        self.assertGreater(len(self.fsm.evts), 0)
        
        evcnt = 0
        ev = self.fsm.evts[evcnt]
        self.assertIn('reason', ev)
        self.assertEqual(ev['reason'], 'conn')
        self.assertIn('cbdata', ev)
        self.assertIn('conn', ev['cbdata'])
        self.assertFalse(ev['cbdata']['conn'])





    

if __name__ == '__main__':
    unittest.main(verbosity=2)

exit(0)












################################################################################

# ESEMPIO DI UTILIZZO

    
    
                
class fsmTest(fsmBase):
    def __init__(self, name, **args):
        fsmBase.__init__(self, name)
        self.counter = self.input("testcounter")
        statesWithIOs = {
            "uno" : [self.counter],
            "due" : [self.counter],
            "tre" : [self.counter],
            "quattro" : [self.counter],
            "cinque" : [self.counter],
            "sei" : [self.counter],
            "sette" : [self.counter]
        }
        self.setSensLists(statesWithIOs)
        self.gotoState('uno')
        print self._mirrors

    def uno_eval(self):
        if self.counter.val() == 0:
            self.gotoState("due")    

    def due_eval(self):
        if self.counter.val() == 1:
            self.gotoState("tre")    
            
    def tre_eval(self):
        if self.counter.val() == 2:
            self.gotoState("quattro")    
        
    def quattro_eval(self):
        if self.counter.val() == 3:
            self.gotoState("cinque")    
 
    def cinque_eval(self):
        if self.counter.val() == 4:
            self.gotoState("sei")    
 
    def sei_eval(self):
        if self.counter.val() == 5:
            self.gotoState("sette")    
 
    def sette_eval(self):
        if self.counter.val() == 6:
            self.gotoState("uno")    
 
    def common_eval(self):
        if self.tmrExp("timer"):
            self.logI("Timer expired")
            self.gotoState("uno")    
 
            
            
if __name__ == '__main__':        
    fsm = fsmTest('fsmTest')
    fsm.eval_forever()
    
        
            
            
