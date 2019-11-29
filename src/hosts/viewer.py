#! /usr/bin/python

# Usage: python viewer.py <num_frames> <service_ip> <key>


import sys
import os
import subprocess


ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + "/../.."
OUTPUT_DIR = ROOT_DIR + "/output"


class Viewer:
    """
    Viewer pulling RTMP live stream with MPlayer.
    """

    def __init__(self, service_ip, key):
        """
        Initialization.

        Args:
            service_ip: IP address of the CDN node.
            key: Livestreaming key.
        """
        self.service_ip = service_ip
        self.key = key
        self.outfile = OUTPUT_DIR + "/hv.log"
        if os.path.exists(self.outfile):
            os.remove(self.outfile)


    def watch(self, num_frames):
        """
        Perform a broadcast.

        Args:
            num_frames: Number of frames to watch before termination.

        """
        command = [
            # "stdbuf", "-i0", "-e0", "-o0",
            # "annotate-output",
            "mplayer",
            "-nocorrect-pts",
            "-nocache",
            "-nosound",
            "-vo", "null",
            "-noidle",
            "-frames", str(num_frames),
            "rtmp://%s/live/%s" % (self.service_ip, self.key),
            "2>&1",
            ">", self.outfile
        ]
        command = ' '.join(command)
        print "CMD: " + command
        os.system(command)  # Subprocess seems not working for redirection.
        os.system("date +\%s\%3N >> " + self.outfile)  # Milliseconds timestamp.


if __name__ == "__main__":
    assert len(sys.argv)==4
    num_frames, service_ip, key = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    viewer = Viewer(service_ip, key)
    viewer.watch(num_frames)
