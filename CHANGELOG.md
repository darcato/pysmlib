# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## To Do

- Using Queque to handle multithreading
- New interface to access IO via fsmBase methods
- Simplified interface between IOs and fsmBase
- Introducing event objects

## [2.0.0] - 2018-08-28

### Added

- Packaging
- New name
- New fsmLoader to simplify the loading scripts, incorporating common stuff.
- Test code (first snippets)
- Test ioc
- Examples
- Usage and documentation
- Integrated watchdog logic

### Changed

- Moving to a single repository for the library
- fsmBase input() renamed to connect()
- fsmBase tmrExp() renamed to tmrExpired()
- fsmIO access methods renamed
    - hasPutCompleted() -> putCompleting()
    - hasChanged() -> changing()
    - hasDisconnected() -> disconnecting()
    - hasConnected() -> connecting()
    - hasFirstValue() -> initializing()
- is_io_connected() renamed to isIoConnected()
- Renamed lnlPvs class to mappedIOs
- Renamed fsmIO to epicsIO
- Renamed mirrorIO to fsmIO
- Renamed fsmLoggerToFile to fsmFileLogger


## [1.0.0] - 2018-02-22

The working version initially used by RF control system at LNL.