#! /usr/bin/python

# Usage: python viewer.py <listen_port>


import sys
import socket
import time
import struct
from common import *


class Viewer:
    """
    Viewer opening a socket and listening on incoming frames.
    """

    def __init__(self, port):
        """
        Initialize with a socket binding to incoming frames on PORT.
        """
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', port))
        self.latency_measures = []  # List of frame latencies in secs.

    def view(self):
        """
        Accept frames for a full broadcast. Must be a complete broadcast because
        it depends on 'bcast_beg' & 'bcast_end' control messages.
        """

        def _recv_frame(bsock, latency_measures):
            """
            Receive a frame from connection socket BSOCK.
            Returns true if receiving a frame, or false if 'bcast_end' signal received.
            """
            # Loop until a 'frame_start' signal.
            while True:
                msg = bsock.recv(CTRL_MSG_LEN)
                if msg == FRAME_BEG:    # Frame start.
                    break
                if msg == BCAST_END:    # Broadcast ends, return false.
                    return False
            # Receive header & content.
            header = bsock.recv(TIMESTAMP_LEN)
            frame = bsock.recv(FRAME_SIZE)
            while len(frame) < FRAME_SIZE:      # A frame may split into multiple packets.
                frame += bsock.recv(FRAME_SIZE-len(frame))
            assert(len(frame)==FRAME_SIZE)
            # Process the header to calculate latency for this frame.
            frame_send_time = parse_timestamp(header)
            current_time = time.time()
            print "  Frame sent@ {:.2f}, recv@ {:.2f}".format(frame_send_time, current_time)
            self.latency_measures.append(current_time-frame_send_time)
            return True

        # Waiting for broadcaster connection & spawn BSOCK for communication.
        print "Viewer listening on port {}...".format(self.port)
        self.sock.listen(5)
        bsock, baddr = self.sock.accept()
        print "Sender {} connected.".format(baddr)
        # Receiving broadcast frames.
        assert(bsock.recv(CTRL_MSG_LEN)==BCAST_BEG)
        frame_cnt = 0
        while _recv_frame(bsock, self.latency_measures):
            frame_cnt += 1
        print "Received {} frames!".format(frame_cnt)

    def avg_latency_ms(self):
        """
        Get average latency in ms, with 10ms-level accuracy.
        """
        avg_latency_secs = sum(self.latency_measures) / len(self.latency_measures)
        return int(round(avg_latency_secs * 1000.))


if __name__ == "__main__":
    assert(len(sys.argv)==2)
    port = int(sys.argv[1])
    viewer = Viewer(port)
    viewer.view()
    print "Avg. latency: {} ms.".format(viewer.avg_latency_ms())
