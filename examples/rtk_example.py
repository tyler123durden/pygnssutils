"""
pygnssutils - rtk_example.py

*** FOR ILLUSTRATION ONLY - NOT FOR PRODUCTION USE ***

RUN FROM WITHIN /examples FOLDER.

PLEASE RESPECT THE TERMS OF USE OF ANY NTRIP CASTER YOU
USE WITH THIS EXAMPLE - INAPPROPRIATE USE CAN RESULT IN
YOUR NTRIP USER ACCOUNT OR IP BEING TEMPORARILY BLOCKED.

This example illustrates how to use the UBXReader and
GNSSNTRIPClient classes to get RTCM3 RTK data from a
designated NTRIP caster/mountpoint and apply it to an
RTK-compatible GNSS receiver (e.g. ZED-F9P) connected to
a local serial port (USB or UART1).

GNSSNTRIPClient receives RTCM data from the NTRIP caster
and outputs it to a message queue. An example GNSSSkeletonApp
class reads data from this queue and sends it to the receiver,
while reading and parsing data from the receiver and printing
it to the terminal.

GNSSNtripClient optionally sends NMEA GGA position sentences
to the caster at a prescribed interval, using either fixed
reference coordinates or live coordinates from the receiver.

NB: Some NTRIP casters may stop sending RTK data after a while
if they're not receiving legitimate NMEA GGA position updates
from the client.

Created on 5 Jun 2022

:author: semuadmin
:copyright: SEMU Consulting © 2022
:license: BSD 3-Clause
"""
# pylint: disable=invalid-name

from queue import Queue, Empty
from threading import Event
from time import sleep

from pygnssutils import VERBOSITY_LOW, GNSSNTRIPClient
from gnssapp import GNSSSkeletonApp

CONNECTED = 1

if __name__ == "__main__":
    # GNSS receiver serial port parameters - AMEND AS REQUIRED:
    SERIAL_PORT = "/dev/ttyACM0"
    BAUDRATE = 38400
    TIMEOUT = 10

    # NTRIP caster parameters - AMEND AS REQUIRED:
    # Ideally, mountpoint should be <30 km from location.
    IPPROT = "IPv4"  # or "IPv6"
    NTRIP_SERVER = "yourcaster"
    NTRIP_PORT = 2101
    FLOWINFO = 0  # for IPv6
    SCOPEID = 0  # for IPv6
    MOUNTPOINT = "yourmountpoint"  # leave blank to retrieve sourcetable
    NTRIP_USER = "youruserid"
    NTRIP_PASSWORD = "yourpassword"

    # NMEA GGA sentence status - AMEND AS REQUIRED:
    GGAMODE = 0  # use fixed reference position (0 = use live position)
    GGAINT = 60  # interval in seconds (-1 = do not send NMEA GGA sentences)
    # Fixed reference coordinates (only used when GGAMODE = 1) - AMEND AS REQUIRED:
    REFLAT = 51.176534
    REFLON = -2.15453
    REFALT = 40.8542
    REFSEP = 26.1743

    recv_queue = Queue()  # data from receiver placed on this queue
    send_queue = Queue()  # data to receiver placed on this queue
    stop_event = Event()
    idonly = True

    try:
        print(f"Starting GNSS reader/writer on {SERIAL_PORT} @ {BAUDRATE}...\n")
        with GNSSSkeletonApp(
            SERIAL_PORT,
            BAUDRATE,
            TIMEOUT,
            stopevent=stop_event,
            recvqueue=recv_queue,
            sendqueue=send_queue,
            idonly=idonly,
            enableubx=True,
            showhacc=True,
        ) as gna:
            gna.run()
            sleep(2)  # wait for receiver to output at least 1 navigation solution

            print(f"Starting NTRIP client on {NTRIP_SERVER}:{NTRIP_PORT}...\n")
            with GNSSNTRIPClient(gna, verbosity=VERBOSITY_LOW) as gnc:
                streaming = gnc.run(
                    ipprot=IPPROT,
                    server=NTRIP_SERVER,
                    port=NTRIP_PORT,
                    flowinfo=FLOWINFO,
                    scopeid=SCOPEID,
                    mountpoint=MOUNTPOINT,
                    ntripuser=NTRIP_USER,  # pygnssutils>=1.0.12
                    ntrippassword=NTRIP_PASSWORD,  # pygnssutils>=1.0.12
                    reflat=REFLAT,
                    reflon=REFLON,
                    refalt=REFALT,
                    refsep=REFSEP,
                    ggamode=GGAMODE,
                    ggainterval=GGAINT,
                    output=send_queue,  # send NTRIP data to receiver
                )

                while (
                    streaming and not stop_event.is_set()
                ):  # run until user presses CTRL-C
                    if recv_queue is not None:
                        # consume any received GNSS data from queue
                        try:
                            while not recv_queue.empty():
                                (raw, parsed) = recv_queue.get(False)
                                print(
                                    f"{'GNSS>> ' + parsed.identity if idonly else parsed}"
                                )
                                recv_queue.task_done()
                        except Empty:
                            pass
                    sleep(1)
                sleep(1)

    except KeyboardInterrupt:
        stop_event.set()
        print("Terminated by user")
