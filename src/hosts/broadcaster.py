#! /usr/bin/python

# Usage: python broadcaster.py <my_ip> <video_file> <service_ip>


import sys
import os
import subprocess
import socket
import signal
from multiprocessing import Process
from common import *


class Broadcaster(object):
    """
    Broadcaster doing RTMP livestreaming with FFmpeg.

    NOTE: MUST be invoked after the viewer!
    """

    def __init__(self, my_ip, video_file, service_ip):
        """
        Initialization.

        Args:
            my_ip: My IP address.
            video_file: Video file to broadcast.
            service_ip: IP address of the CDN node.
            key: Livestreaming key.
            notify_sock: P2P notification socket.
        """
        self.my_ip = my_ip
        self.video_file = ROOT_DIR + "/" + video_file
        self.service_ip = service_ip
        self.key = STREAM_KEY
        self.notify_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.b2s_proc = None
        self.b2v_procs = []

        # Register signal catchers.
        signal.signal(signal.SIGINT, self._exit_on_kill)
        signal.signal(signal.SIGTERM, self._exit_on_kill)


    def _exit_on_kill(self, signum=None, frame=None):
        """
        Cleaning up things...
        """
        print "[BCAST] Cleaning up..."
        try:
            if self.b2s_proc is not None:
                self.b2s_proc.terminate()
            for b2v_proc in self.b2v_procs:
                b2v_proc.terminate()
        except:
            pass
        os.system("killall ffmpeg")
        exit(0)


    def broadcast(self):
        """
        Perform a broadcast.
        """

        def _stream_service(target_ip, out_file):
            """
            Establish a livestreaming connection to service.

            Args:
                target_ip: Destination IP.
                out_file: Logging file.
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
                "rtmp://%s/live/%s" % (target_ip, self.key),
                "2>&1",     # FFmpeg writes to stderr!!!
                ">", out_file
            ]
            command = ' '.join(command)
            print "CMD: " + command
            os.system(command)
            os.system("date +\%s\%3N >> " + out_file)   # Milliseconds timestamp.

        def _stream_peer(target_ip, out_file):
            """
            Establish a livestreaming connection to peer viewer.

            Args:
                target_ip: Destination IP.
                out_file: Logging file.
            """
            command = [
                # "stdbuf", "-i0", "-e0", "-o0",
                # "annotate-output",
                "ffmpeg",
                "-re",
                "-i", self.video_file,
                "-flvflags", "no_duration_filesize",
                #"-max_muxing_queue_size", "8192",
                "-f", "flv",
                "tcp://%s:%d" % (target_ip, PEER_PORT),
                "2>&1",     # FFmpeg writes to stderr!!!
                ">", out_file
            ]
            command = ' '.join(command)
            print "CMD: " + command
            os.system(command)
            os.system("date +\%s\%3N >> " + out_file)   # Milliseconds timestamp.

        # Open a thread to stream to the CDN service server node.
        b2s_log = OUTPUT_DIR + "/b2s.log"
        if os.path.exists(b2s_log):
            os.remove(b2s_log)
        self.b2s_proc = Process(target=_stream_service, args=(self.service_ip, b2s_log))
        self.b2s_proc.start()
        print "[BCAST] Broadcaster -> Service livestreaming START"

        # Listen on the notification socket. If a P2P notification arrives, start
        # a new streaming directly to the viewers location.
        self.notify_sock.connect((self.service_ip, NOTIFY_PORT))
        while True:
            notify_data = self.notify_sock.recv(1024).strip()
            if not notify_is_heartbeat(notify_data):
                # Broadcaster -> Service connection still maintained.
                viewer_ip = parse_notify_ip(notify_data)
                b2v_log = OUTPUT_DIR + "/b2v-" + viewer_ip + ".log"
                if os.path.exists(b2v_log):
                    os.remove(b2v_log)
                b2v_proc = Process(target=_stream_peer, args=(viewer_ip, b2v_log))
                b2v_proc.start()
                self.b2v_procs.append(b2v_proc)
                print "[BCAST] Broadcaster -> Viewer (%s) P2P START" % (viewer_ip,)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Usage: python src/hosts/broadcaster.py <my_ip> <video_file> <service_ip>"
        exit(1)
    assert len(sys.argv) == 4
    my_ip, video_file, service_ip = sys.argv[1], sys.argv[2], sys.argv[3]
    broadcaster = Broadcaster(my_ip, video_file, service_ip)
    broadcaster.broadcast()
