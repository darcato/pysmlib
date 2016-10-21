#! /usr/bin/python

from threading import Thread, enumerate
import signal
from time import sleep
import argparse

from waves import waves
from caraterize import caraterize
from pulseRf import pulseRf
from zeroFreq import zeroFreq
from fsm import fsmTimers, cavityPVs

class fsmThread(Thread):
	def __init__(self, fsm):
		Thread.__init__(self)
		self.fsm = fsm

	def run(self):
		print("Starting fsm: %s " % self.fsm.fsmname())
		self.fsm.eval_forever()
		print("Stopped fsm: %s " % self.fsm.fsmname())

def main():
	parser = argparse.ArgumentParser(description="rfDaemon - loads the required fsm to perform procedures")
	parser.add_argument("configFile", help="the path of the configuration file", type=str)
	parser.add_argument("-v", "--verbosity", help="set the debug level", default=0, type=int)
	args = parser.parse_args()
	
	file = open(args.configFile, "r")
	lines = file.readlines()
	file.close()

	targets = {}
	for line in lines:
		if line.startswith("#"):
			continue
		columns=line.split('=')
		cryostat = int(columns[0])
		cavitiesStr = columns[1].split(",")
		cavities = []
		for cavity in cavitiesStr:
			cavities.append(int(cavity))
		targets[cryostat]=cavities

	#create a thread for the timer manager
	timerManager = fsmTimers()
	commonIos = cavityPVs()
	#timerManager.start()  #will be done automatically from first fsm loaded

	#a dictitonary containing fsm objects as keys and their thread (or None) as values
	fsms = {}
	for cryostat, cavities in targets.iteritems():
		for cavity in cavities:
			name = "Cr%02d.%1d-" % (cryostat, cavity)
			w = waves(name+"WAVE", cryostat, cavity, tmgr=timerManager, ios=commonIos)
			c = caraterize(name+"CARA", cryostat, cavity, tmgr=timerManager, ios=commonIos)
			z = zeroFreq(name+"ZRFR", cryostat, cavity, tmgr=timerManager, ios=commonIos)
			p = pulseRf(name+"PULS", cryostat, cavity, tmgr=timerManager, ios=commonIos)
			fsms.update({w:None, c:None, z:None, p:None})


	for fsm in fsms.iterkeys():
		newThread = fsmThread(fsm)
		newThread.start()
		fsms[fsm]=newThread
	print("All fsms started!")

	sleep(0.1)
	for i in enumerate():
		print(i)
	print args
	print type(args)
	print args.configFile
	print targets
	for i in fsms:
		print i

	def killAll(signum, frame):
		print("%d -> Going to kill all fsms" % signum)
		for fsm, thread in fsms.iteritems():
			fsm.kill()
			thread.join()
		print("Killed all the fsms")
		if timerManager.isAlive():  #if no fsm is loaded it won't be alive
			timerManager.kill()
		print("Killed the timer manager")
	
	signal.signal(signal.SIGINT, killAll)
	signal.pause()


if __name__ == '__main__':        
	main()