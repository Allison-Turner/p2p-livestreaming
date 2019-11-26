#! /usr/bin/python

# Usage: python broadcaster.py <target_host> <target_port>


import sys
import os
import socket
import random
import time
import struct
import threading
from common import *


class Broadcaster:
    """
    Broadcaster sending out live video frames through a socket.
    """

    def __init__(self, cdn_host, cdn_port):
        """
        Initialize with a socket connecting to HOST:PORT. Frame rate will be
        very inaccurate because of the implementation of timer and time.sleep()
        in python runtime, so this is actually the max bound of frame rate.
        """
        self.host = cdn_host
        self.port = cdn_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        # Load pre-generated video.
        script_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        self.video = []
        with open(script_dir+"/../video.data", 'rb') as fvideo:
            frame = fvideo.read(FRAME_SIZE)
            while frame:
                self.video.append(frame)
                frame = fvideo.read(FRAME_SIZE)


    def broadcast(self, length):
        """
        Do a broadcast for approximately LENGTH secs in time.
        """

        def _send_frame(video, frame_idx):
            """
            Periodic frame send routine executed every 1sec/frame_rate interval.
            """
            self.sock.sendall(FRAME_BEG)
            header = get_timestamp()    # 4 bytes timestamp.
            frame = video[frame_idx]
            data = header + frame
            self.sock.sendall(data)
            print "  Frame sent@ {:.2f}, length: {}".format(time.time(), len(data))
            self.sock.sendall(FRAME_END)

        def _timer_func(event):
            """
            When timer times up, set the EVENT.
            """
            event.set()

        print "Broadcaster start sending to {}:{}.".format(self.host, self.port)
        self.sock.sendall(BCAST_BEG)
        ticker = threading.Event()
        # Start timer for LENGTH secs.
        threading.Timer(length, _timer_func, args=[ticker]).start()
        # Begin the broadcast at FRAME_RATE frequency. Event.wait(timeout) will return
        # false when timeout and true if event is set, so the above timer will end
        # this while loop eventually.
        frame_idx = 0
        while not ticker.wait(1./FRAME_RATE):
            _send_frame(self.video, frame_idx)
            frame_idx += 1
        self.sock.sendall(BCAST_END)
        print "Broadcast {} frames!".format(frame_idx)


if __name__ == "__main__":
    assert(len(sys.argv)==3)
    host, port = sys.argv[1], int(sys.argv[2])
    broadcaster = Broadcaster(host, port)
    broadcaster.broadcast(10)   # Broadcast for 10 secs.
