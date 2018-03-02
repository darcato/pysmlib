#! /usr/bin/python

# Davide Marcato 03/2018
# An example of a startup script to load an lnlseq daemon


from pysmlib import loader
from examplefsm import examplefsm


## -------------------
# logger options
## -------------------
loader.setVerbosity(2)  ##use only this if you want to print lo to shell
loader.logToFile("mypath", "daemon")  ##use also this if you want to print to file

## -------------------
# inputs options
## -------------------
loader.setIoMap("pathToMapFile")  #this will set the map file path


## -------------------
# load each fsm
## -------------------
loader.load(waves, "WAVE1", 1, "other params")
loader.load(waves, "WAVE2", 2, "other params")

## -------------------
# start execution
## -------------------
loader.start()