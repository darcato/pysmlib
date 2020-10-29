# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

## To Do

- Using Queque to handle multithreading
- New interface to access IO via fsmBase methods
- Simplified interface between IOs and fsmBase
- Introducing event objects
- Using ```ca.replace_printf_handler()``` to silence ca warnings.

## [3.2.0] - 2020-10-29

Adding method to detect the edge on the timer expiration.

### Added

- Added ``tmrExpiring()`` method to access the expiration event.
- Added some tests, using pytest fixtures, pcaspy server and event queue.
- Automatic testing with nox and gitlab-ci.
- Documentation update.

### Changed

- Added ``io.changing()`` now returns ``False`` on the initialization event. Use ``io.initializing()`` instead.

## [3.1.0] - 2020-07-22

Adding support for PV alarms.

### Added

- Added ``I/O`` methods to access alarm value and changing state.
- Added a lot of methods and options to access ``I/O`` properties.
- Documentation update.

## [3.0.0] - 2020-07-15

This version breaks back-compatibility by abandoning support for python 2.

### Changed

- Now supporting python 3.6+ only. Python 2.7 is deprecated.
- Changed ``loader`` to be class-based

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