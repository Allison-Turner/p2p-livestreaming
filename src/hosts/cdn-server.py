#! /usr/bin/python

# Usage: python cdn-server.py


import sys
import os
import time
import socket
import subprocess
import signal
from multiprocessing import Process, Lock
from common import *


class CDN_Server(object):
    """
    CDN server using Nginx RTMP module.
    """

    def __init__(self):
        """
        Initialize the CDN server with notification channels to a broadcaster
        and viewers.
        """
        self.notify_procs = []
        self.notify_lock = Lock()
        self.notify_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.notify_sock.bind(('', NOTIFY_PORT))

        # Register signal catchers.
        signal.signal(signal.SIGINT, self._exit_on_kill)
        signal.signal(signal.SIGTERM, self._exit_on_kill)


    def _exit_on_kill(self, signum=None, frame=None):
        """
        Cleaning up things...
        """
        print "[CDN] Cleaning up..."
        try:
            for notify_proc in self.notify_procs:
                notify_proc.terminate()
        except:
            pass
        os.system("killall nginx")
        os.system("kill $(lsof -t -i:%d)" % (NOTIFY_PORT,))
        exit(0)


    def run(self):
        """
        Runs the Nginx server. Periodically maintains the notification channel
        messages.
        """

        def _notify_heartbeat(nsock, nlock):
            """
            Maintains a notification channel's heartbeat (1s per heartbeat).
            """
            while True:
                nlock.acquire()
                nsock.sendall(HEARTBEAT_DATA)
                nlock.release()
                time.sleep(1)     # Pause 1s.
        
        # Start Nginx.
        os.system("nginx")

        # Receive notification channel connections.
        print "[CDN] Listening on notification channel connections"
        while True:
            self.notify_sock.listen(5)
            nsock, naddr = self.notify_sock.accept()
            notify_proc = Process(target=_notify_heartbeat, args=(nsock, self.notify_lock))
            notify_proc.start()
            self.notify_procs.append(notify_proc)
            print "[CDN] Host %s connected" % (naddr,)


if __name__ == "__main__":
    cdn_server = CDN_Server()
    cdn_server.run()
