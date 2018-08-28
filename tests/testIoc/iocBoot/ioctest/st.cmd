#!../../bin/linux-x86_64/test

## You may have to change test to something else
## everywhere it appears in this file

#< envPaths

## Register all support components
dbLoadDatabase("../../dbd/test.dbd",0,0)
test_registerRecordDeviceDriver(pdbbase) 

## Load record instances
dbLoadRecords("../../db/test.db","user=damiano")

iocInit()

## Start any sequence programs
#seq snctest,"user=damiano"
