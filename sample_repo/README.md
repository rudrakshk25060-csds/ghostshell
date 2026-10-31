# Project Necropolis: The Forgotten Cache Daemon

An experimental, legacy in-memory cache daemon written in the dead of winter.

## Overview
Necropolis was designed to store transient session state across distributed nodes.
Legend has it that whoever committed the initial daemon loop never returned to close the socket.

## Known Anomalies
- Port 6660 occasionally emits phantom keep-alive pulses.
- `ritual.py` contains an unfinished eviction loop.
