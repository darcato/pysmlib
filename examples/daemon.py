#! /usr/bin/python

# Davide Marcato 03/2018
# An example of a startup script to load a pysmlib daemon


from smlib import loader
from myfsm import myfsm


## -------------------
# logger options
## -------------------
loader.setVerbosity(4)  ##use only this if you want to print log to shell
#loader.logToFile("mypath", "daemon")  ##use also this if you want to print to file

## -------------------
# inputs options
## -------------------
#loader.setIoMap("pathToMapFile")  #this will set the map file path


## -------------------
# load each fsm
## -------------------
loader.load(myfsm, "fsm1", "ciao", "-come")
loader.load(myfsm, "fsm2", "ciao")

## -------------------
# start execution
## -------------------
loader.start()