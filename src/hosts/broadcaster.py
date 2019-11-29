#! /usr/bin/python

# Usage: python broadcaster.py <video_file> <service_ip> <key>


import sys
import os
import subprocess


ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + "/../.."
OUTPUT_DIR = ROOT_DIR + "/output"


class Broadcaster:
    """
    Broadcaster doing RTMP livestreaming with FFmpeg.
    """

    def __init__(self, video_file, service_ip, key):
        """
        Initialization.
        Args:
            video_file: Video file to broadcast.
            service_ip: IP address of the CDN node.
            key: Livestreaming key.
        """
        self.video_file = ROOT_DIR + "/" + video_file
        self.service_ip = service_ip
        self.key = key
        self.outfile = OUTPUT_DIR + "/hb.log"
        if os.path.exists(self.outfile):
            os.remove(self.outfile)


    def broadcast(self):
        """
        Perform a broadcast.
        """
        command = [
            # "stdbuf", "-i0", "-e0", "-o0",
            # "annotate-output",
            "ffmpeg",
            "-re",
            "-i", self.video_file,
            "-flvflags", "no_duration_filesize",
            "-max_muxing_queue_size", "8192",
            "-f", "flv",
            "rtmp://%s/live/%s" % (self.service_ip, self.key),
            "2>&1",     # FFmpeg writes to stderr!!!
            ">", self.outfile
        ]
        command = ' '.join(command)
        print "CMD: " + command
        os.system(command)  # Subprocess seems not working for redirection.
        os.system("date +\%s\%3N >> " + self.outfile)  # Milliseconds timestamp.


if __name__ == "__main__":
    assert len(sys.argv)==4
    video_file, service_ip, key = sys.argv[1], sys.argv[2], sys.argv[3]
    broadcaster = Broadcaster(video_file, service_ip, key)
    broadcaster.broadcast()
