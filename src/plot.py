#!/bin/python


import os
import sys
import numpy as np
import matplotlib.pyplot as plt


ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + "/.."
RESULT_DIR = ROOT_DIR + "/results"


def plot_delays():
    """
    Plot the delays from experiment ping results.
    """
    stream_interval = (15, 45)

    # Read 60 secs from direct-b2s.
    direct_delays = []
    with open(RESULT_DIR+"/direct-b2s.ping", 'r') as fd:
        fd.readline()
        for i in range(60):
            line = fd.readline().strip()
            rtt = int(line[line.rfind('=')+1:line.rfind('ms')-1])
            direct_delays.append(rtt/2)
            
    # Read 60 secs from direct-s2v, and add to the direct delays.
    with open(RESULT_DIR+"/direct-s2v.ping", 'r') as fd:
        fd.readline()
        for i in range(60):
            line = fd.readline().strip()
            rtt = int(line[line.rfind('=')+1:line.rfind('ms')-1])
            direct_delays[i] += (rtt/2)

    # Read 60 secs from bypass-b2v.
    bypass_delays = []
    with open(RESULT_DIR+"/bypass-b2v.ping", 'r') as fd:
        fd.readline()
        for i in range(60):
            line = fd.readline().strip()
            rtt = int(line[line.rfind('=')+1:line.rfind('ms')-1])
            bypass_delays.append(rtt/2)

    # Plotting.
    plt.plot(direct_delays, c='b', label="Original")
    plt.plot(bypass_delays, c='r', label="Bypassed")
    plt.axvline(x=stream_interval[0], linestyle='--', c='0.5')
    plt.axvline(x=stream_interval[1], linestyle='--', c='0.5',
                label="Streaming interval")
    plt.xlabel("Time (s)")
    plt.ylabel("Delay (ms)")
    plt.legend()
    plt.savefig(RESULT_DIR+"/delay-plot.png")


if __name__ == "__main__":
    plot_delays()
