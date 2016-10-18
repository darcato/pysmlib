#! /usr/bin/python

from threading import Thread, enumerate
import signal
from time import sleep
import argparse

from waves import waves
from caraterize import caraterize
from pulseRf import pulseRf
from zeroFreq import zeroFreq
from fsm import fsmTimers

class fsmThread(Thread):
	def __init__(self, fsm):
		Thread.__init__(self)
		self.fsm = fsm

	def run(self):
		print("Starting fsm: %s " % self.fsm.name())
		self.fsm.eval_forever()
		print("Stopped fsm: %s " % self.fsm.name())

def main():
	parser = argparse.ArgumentParser(description="rfDaemon - loads the required fsm to perform procedures")
	parser.add_argument("configFile", help="the path of the configuration file", type=str)
	parser.add_argument("-v", "--verbosity", help="set the debug level", default=0, type=int)
	args = parser.parse_args()
	print args



	#create a thread for the timer manager
	timerManager = fsmTimers()
	#timerManager.start()  #will be done automatically from first fsm loaded

	#a dictitonary containing fsm objects as keys and their thread (or None) as values
	fsms = {}
	fsms[waves('waves', tmgr=timerManager)] = None
	fsms[caraterize('caraterize', tmgr=timerManager)] = None

	for fsm in fsms.iterkeys():
		newThread = fsmThread(fsm)
		newThread.start()
		fsms[fsm]=newThread
	print("All fsms started!")

	sleep(0.1)
	for i in enumerate():
		print(i)

	def killAll(signum, frame):
		print("%d -> Going to kill all fsms" % signum)
		for fsm, thread in fsms.iteritems():
			fsm.trigger(stop_fsm=True)
			thread.join()
		print("Killed all the fsms")
		timerManager.kill()
		print("Killed the timer manager")
	
	signal.signal(signal.SIGINT, killAll)
	signal.pause()


if __name__ == '__main__':        
	main()