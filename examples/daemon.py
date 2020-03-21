#! /usr/bin/python
# -*- coding: utf-8 -*-
'''
An example of a startup script to load a pysmlib daemon

@date: March 2018
@author: Davide Marcato
@email: davide.marcato@lnl.infn.it
'''

from smlib import loader
from myfsm import myfsm

l = loader()

## -------------------
# logger options
## -------------------
l.setVerbosity(4)  ##use only this if you want to print log to shell
#loader.logToFile("mypath", "daemon")  ##use also this if you want to print to file

## -------------------
# inputs options
## -------------------
#l.setIoMap("pathToMapFile")  #this will set the map file path


## -------------------
# load each fsm
## -------------------
l.load(myfsm, "fsm1", "ciao", "-come")
l.load(myfsm, "fsm2", "ciao")

## -------------------
# start execution
## -------------------
l.start()
