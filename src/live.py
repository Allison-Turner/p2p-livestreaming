#!/usr/bin/python

# Usage: sudo python src/live.py <video_file> <dump_file>

#
# Currently the OpenFlow switch can only support the simple topology with 1 viewer
# and can only be compatible very rigid RTMP logics ;)
#


import sys
import os
import time
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.node import RemoteController, OVSSwitch
from mininet.util import dumpNodeConnections
from topo import LivestreamingSingleTopo


ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + "/.."
OUTPUT_DIR = ROOT_DIR + "/output"


def _launch_service(net):
    """
    Launch the CDN service (an Nginx RTMP server).
    """
    hs = net.get('hs')
    hs.cmd('python %s/src/hosts/cdn-server.py &' % (ROOT_DIR,))
    time.sleep(1)   # Ensure correct startup.


def _do_livestreaming(net, video_file, dump_file):
    """
    Perform full livestreaming procedure. The viewer must be launched before
    the broadcaster so that it meets the current naive OpenFlow switch's
    RTMP processing logic!

    Args:
        video_file: Name of the video file to broadcast.
    """
    hb, hs, hv = net.get('hb', 'hs', 'hv1')

    # Launch the viewer FIRST.
    print "Viewer 1 UP"
    hv.cmd("python %s/src/hosts/viewer.py %s %s %s &" %
           (ROOT_DIR, hv.IP(), dump_file, hs.IP()))
    time.sleep(10)  # Ensure viewer's connection.
    
    # Launch broadcaster & start the streaming.
    print "Broadcaster UP: \'%s\'" % (video_file,)
    hb.cmd("python %s/src/hosts/broadcaster.py %s %s %s &" %
           (ROOT_DIR, hb.IP(), video_file, hs.IP()))

    # Perform the streaming experiment for sufficiently long time.
    time.sleep(30)
    print "Livestreaming experiment FINISH ;)"


def _clean_all(net):
    """
    Kill all hosts' scripts.
    """
    hb, hs, hv = net.get('hb', 'hs', 'hv1')
    hs.cmd("kill $(pgrep -f cdn-server.py)")
    hb.cmd("kill $(pgrep -f broadcaster.py)")
    hv.cmd("kill $(pgrep -f viewer.py)")


def _parse_delay(net):
    """
    Parse delay in milliseconds, assuming correct logging.
    """
    hv = net.get('hv1')
    with open(OUTPUT_DIR+"/b2v-"+hv.IP()+".log") as fb, \
         open(OUTPUT_DIR+"/vfp-"+hv.IP()+".log") as fv:
        tb = int([l.strip() for l in fb.read().split('\n') if l][-1])
        tv = int([l.strip() for l in fv.read().split('\n') if l][-1])
        return tv - tb


def livestremaing_test(video_file, dump_file):
    """
    Create a livestreaming topology and run a delay test.
    """
    topo = LivestreamingSingleTopo(num_viewers=1)
    net = Mininet(topo=topo, link=TCLink, controller=RemoteController,
                  switch=OVSSwitch, autoSetMacs=True)
    net.start()
    print "(ignore the above controller warning on port :6653)"

    # Dump the topology.
    print "### Topology ###"
    dumpNodeConnections(net.hosts)
    
    # Test connectivity. This "pingall" test also gives the L2 learning switch a
    # chance to pre-learn the MAC-port mapping.
    print "### Ping all ###"
    net.pingAll()
    
    # Launch the nodes apps to perform a live streaming test.
    print "### Live streaming ###"
    _launch_service(net)
    _do_livestreaming(net, video_file, dump_file)
    _clean_all(net)
    
    # Parse the delay from the two logs 'output/hb.log', 'output/hv.log'.
    print "### Results ###"
    print "Delta in termination = %d ms" % (_parse_delay(net),)
    net.stop()


if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    if len(sys.argv) != 3:
        print "Usage: python src/live.py <video_file> <dump_file>"
        exit(1)
    assert len(sys.argv) == 3
    video_file, dump_file = sys.argv[1], sys.argv[2]
    livestremaing_test(video_file, dump_file)
