#!/bin/bash

TESTDIR=$(pwd)
ARCH=$($EPICS_BASE/startup/EpicsHostArch)
IOC=$(pwd)/testIoc/bin/$ARCH/test
IOCRUNDIR=$(pwd)/testIoc/iocBoot/ioctest/



if [ "$1" = "run" ]
then
    if [ "$(screen -list | grep 'testioc')" != "" ]
    then
        echo "Test ioc already running..."
    else
        if [ ! -x $IOC ]
        then
            echo "Building test IOC..."    
            if ! make -C testIoc > /dev/null || ! [ -x $IOC ]
            then
                echo "Could not build test IOC"    
                exit 1
            fi
        fi
        echo "Running IOC in screen session named ""testioc""..."    
        if ! cd $IOCRUNDIR  || ! screen -S testioc -d -m $IOC st.cmd || ! cd $TESTDIR [ "$(screen -list | grep 'testioc')" = "" ]
        then
            echo "Could not run IOC"
            exit 1
        fi
    fi
fi


if [ "$1" = "stop" ]
then
    echo "Stopping test IOC..."
    screen -S testioc -X kill > /dev/null    
fi





