#!/usr/bin/python

# Usage: sudo python live.py


import sys
import os
import time
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from topo import LivestreamingTopo


VIEWER_PORT, CDN_PORT = 50007, 50008
TEST_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))
OUTPUT_DIR = TEST_DIR + "/output"


def _parse_latency(fv_name):
    """
    Extract last line of viewer's output, which contains the avg. latency.
    """
    with open(fv_name, 'r') as fv:
        lines = fv.readlines()
        assert len(lines)>1
        last = lines[-1].strip()
        assert len(last)>0
        return last


def _original_livestreaming(net):
    """
    Original livestreaming flow through CDN: h1 -> h3 -> h2.
    """
    hb, hv, hcdn = net.get('h1', 'h2', 'h3')
    # Run test.
    hv.cmd('python hosts/viewer.py {} > {}/original-hv.log &'
           .format(VIEWER_PORT, OUTPUT_DIR))
    time.sleep(1)   # Ensure viewer startup.
    hcdn.cmd('python hosts/cdn-server.py {} {} {} > {}/original-hcdn.log &'
             .format(CDN_PORT, hv.IP(), VIEWER_PORT, OUTPUT_DIR))
    time.sleep(1)   # Ensure CDN server startup.
    hb.cmd('python hosts/broadcaster.py {} {} > {}/original-hb.log'
           .format(hcdn.IP(), CDN_PORT, OUTPUT_DIR))
    time.sleep(1)   # Wait for graceful shutdown of viewer & CDN server.
    # Parse latency from viewer output.
    print _parse_latency("{}/original-hv.log".format(OUTPUT_DIR))


def _bypassed_livestreaming(net):
    """
    Bypassed livestreaming: h1 -> h2 directly. Currently no OpenFlow interference.
    """
    hb, hv = net.get('h1', 'h2')
    # Run test.
    hv.cmd('python hosts/viewer.py {} > {}/bypassed-hv.log &'
           .format(VIEWER_PORT, OUTPUT_DIR))
    time.sleep(1)   # Ensure viewer startup.
    hb.cmd('python hosts/broadcaster.py {} {} > {}/bypassed-hb.log'
           .format(hv.IP(), VIEWER_PORT, OUTPUT_DIR))
    time.sleep(1)   # Wait for graceful shutdown of viewer.
    # Parse latency from viewer output.
    print _parse_latency("{}/bypassed-hv.log".format(OUTPUT_DIR))


def livestremaing_test():
    """
    Create a livestreaming topology and run both original & bypassed livestreaming
    proof-of-concpet tests.
    """
    topo = LivestreamingTopo()
    net = Mininet(topo=topo, link=TCLink)
    net.start()
    # Dump the topology.
    print "### Topology ###"
    dumpNodeConnections(net.hosts)
    # Test connectivity.
    print "### Ping all ###"
    net.pingAll()
    # Perform original livestreaming with CDN.
    print "### Testing: original ###"
    _original_livestreaming(net)
    # Perform bypassed livestreaming.
    print "### Testing: bypassed ###"
    _bypassed_livestreaming(net)
    net.stop()


if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    livestremaing_test()
