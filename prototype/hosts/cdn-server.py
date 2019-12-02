#! /usr/bin/python

# Usage: python cdn-server.py <listen_port> <viewer_host> <viewer_port>


import sys
import socket
import time
import struct
from common import *


class CDN_Server:
    """
    CDN server listens on the broadcaster, stores the frames received, and then transmit
    them down to the viewer.
    """

    def __init__(self, listen_port, viewer_host, viewer_port):
        """
        Initialize with two sockets, one listening on broadcaster, and the other one
        pushing the frames down to viewer.
        """
        self.listen_port = listen_port
        self.viewer_host = viewer_host
        self.viewer_port = viewer_port
        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.bind(('', listen_port))
        self.viewer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.viewer_sock.connect((viewer_host, viewer_port))
        self.storage = []

    def run(self):
        """
        Runs the CDN server logic.
        """

        def _recv_frame(bsock, storage):
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
            assert len(frame)==FRAME_SIZE
            # Process the header to calculate latency for this frame.
            frame_send_time = parse_timestamp(header)
            current_time = time.time()
            print "  Frame sent@ {:.2f}, recv@ {:.2f}".format(frame_send_time, current_time)
            storage.append(frame)   # Store the received frame.
            return True

        def _push_frame(vsock, storage):
            """
            Pushes the last frame in stroage to viewer VSOCK.
            """
            vsock.sendall(FRAME_BEG)
            header = get_timestamp()    # 4 bytes timestamp.
            frame = storage[-1]
            data = header + frame
            vsock.sendall(data)
            print "  Frame sent@ {:.2f}, length: {}".format(time.time(), len(data))
            vsock.sendall(FRAME_END)

        # Waiting for broadcaster connection & spawn BSOCK for communication.
        print "CDN server will transmit frames to {}:{}.".format(self.viewer_host,
                                                                 self.viewer_port)
        print "CDN server listening on port {}...".format(self.listen_port)
        self.listen_sock.listen(5)
        bsock, baddr = self.listen_sock.accept()
        print "Sender {} connected.".format(baddr)
        # Receiving broadcast frames & notify viewer with 'bcast_beg' as well.
        assert bsock.recv(CTRL_MSG_LEN)==BCAST_BEG
        self.viewer_sock.sendall(BCAST_BEG)
        frame_cnt = 0
        while _recv_frame(bsock, self.storage):
            frame_cnt += 1
            _push_frame(self.viewer_sock, self.storage)
        # Remember to notify viewer about 'bcast_end'.
        self.viewer_sock.sendall(BCAST_END)
        print "Processed {} frames!".format(frame_cnt)


if __name__ == "__main__":
    assert len(sys.argv)==4
    listen_port, viewer_host, viewer_port = int(sys.argv[1]), sys.argv[2], int(sys.argv[3])
    cdn_server = CDN_Server(listen_port, viewer_host, viewer_port)
    cdn_server.run()
