#! /usr/bin/python

# Usage: python viewer.py <my_ip> <dump_file> <service_ip>


import sys
import os
import subprocess
import socket
import signal
from multiprocessing import Process
from common import *


class Viewer(object):
    """
    Viewer pulling RTMP live stream with MPlayer.

    NOTE: MUST be invoked before the broadcaster!
    """

    def __init__(self, my_ip, dump_file, service_ip):
        """
        Initialization.

        Args:
            my_ip: My IP address.
            service_ip: IP address of the CDN node.
            key: Livestreaming key.
            notify_sock: P2P notification socket.
        """
        self.my_ip = my_ip
        self.dump_file = ROOT_DIR + "/" + dump_file
        self.service_ip = service_ip
        self.key = STREAM_KEY
        self.notify_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.vfs_proc = None
        self.vfp_proc = None

        # Register signal catchers.
        signal.signal(signal.SIGINT, self._exit_on_kill)
        signal.signal(signal.SIGTERM, self._exit_on_kill)


    def _exit_on_kill(self, signum=None, frame=None):
        """
        Cleaning up things...
        """
        print "[VIEW] Cleaning up..."
        try:
            if self.vfs_proc is not None:
                self.vfs_proc.terminate()
            if self.vfp_proc is not None:
                self.vfp_proc.terminate()
        except:
            pass
        os.system("killall mplayer")
        exit(0)


    def watch(self):
        """
        Watch a livestream.
        """

        def _view_service(source_ip, out_file):
            """
            Establish a livestreaming connection from service.

            Args:
                source_ip: Source IP.
                out_file: Logging file.
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
                # "-frames", str(num_frames),
                "-dumpstream", "-dumpfile", self.dump_file,
                "rtmp://%s/live/%s" % (source_ip, self.key),
                "2>&1",
                ">", out_file
            ]
            command = ' '.join(command)
            print "CMD: " + command
            os.system(command)
            os.system("date +\%s\%3N >> " + out_file)   # Milliseconds timestamp.

        def _view_peer(out_file):
            """
            Establish a livestreaming connection from peer broadcaster.

            Args:
                out_file: Logging file.
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
                # "-frames", str(num_frames),
                "-dumpstream", "-dumpfile", self.dump_file,
                "ffmpeg://tcp://%s:%d?listen" % (self.my_ip, PEER_PORT),
                "2>&1",
                ">", out_file
            ]
            command = ' '.join(command)
            print "CMD: " + command
            os.system(command)
            os.system("date +\%s\%3N >> " + out_file)   # Milliseconds timestamp.

        # Open a thread to receive stream from the CDN service.
        vfs_log = OUTPUT_DIR + "/vfs-" + self.my_ip + ".log"
        if os.path.exists(vfs_log):
            os.remove(vfs_log)
        self.vfs_proc = Process(target=_view_service, args=(self.service_ip, vfs_log))
        self.vfs_proc.start()
        print "[VIEW] Viewer <- Service listening START"

        # Listen on the notification port. If the broadcaster is nearby, will
        # receive a notification so we can start listening on his IP instead
        # of the CDN server's.
        self.notify_sock.connect((self.service_ip, NOTIFY_PORT))
        while True:
            notify_data = self.notify_sock.recv(1024).strip()
            if not notify_is_heartbeat(notify_data):

                # Stop the original stream.
                # self.vfs_proc.terminate()     # This will trigger _clean_up routine.
                os.system("killall mplayer")
                if os.path.exists(self.dump_file):
                    os.remove(self.dump_file)
                self.vfs_proc = None
                print "[VIEW] Viewer <- Service connection END"

                # Start the new receiver.
                broadcaster_ip = parse_notify_ip(notify_data)
                vfp_log = OUTPUT_DIR + "/vfp-" + self.my_ip + ".log"
                if os.path.exists(vfp_log):
                    os.remove(vfp_log)
                self.vfp_proc = Process(target=_view_peer, args=(vfp_log,))
                self.vfp_proc.start()
                print "[VIEW] Viewer (%s) <- Broadcaster (%s) P2P START" % \
                      (self.my_ip, broadcaster_ip)

                break   # Viewer breaks the loop when P2P is established.

        if self.vfp_proc is not None:
            self.vfp_proc.join()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print "Usage: python src/hosts/viewer.py <my_ip> <dump_file> <service_ip>"
        exit(1)
    assert len(sys.argv) == 4
    my_ip, dump_file, service_ip = sys.argv[1], sys.argv[2], sys.argv[3]
    viewer = Viewer(my_ip, dump_file, service_ip)
    viewer.watch()
