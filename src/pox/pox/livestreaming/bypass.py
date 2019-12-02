#
# Modified based on the `forwarding.l2_learning` component.
# MIT 6.829 Fall 2019, livestreaming project: Vishrant, Allison, and Guanzhou.
# Initial copyright as follows.
#

# Copyright 2011-2012 James McCauley
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An L2 learning switch, used for P2P bypassed livestremaing scenario.

It is derived from one written live for an SDN crash course.
It is somwhat similar to NOX's pyswitch in that it installs
exact-match rules for each flow.
"""


from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str, str_to_dpid
from pox.lib.util import str_to_bool
import time

log = core.getLogger()


# Hardcoding RTMP constants.
RTMP_PORT = 1935
STREAM_KEY = "6829proj"


# P2P Notification constants.
NOTIFY_PORT = 42857
PEER_PORT = 2000
HEARTBEAT_LENGTH = 15
HEARTBEAT_PADDING = '|'


class RTMPControlPacket(object):
    """
    RTMP packet parser.
    """

    def __init__(self, content):
        """
        Parse and create an RTMP packet object.

        Args:
            content - a bytestring returned from tcp.payload

        Attributes (if not given then default to None):
            chunk_header_type
            chunk_stream_id
            timestamp
            msg_length
            msg_type
            msg_stream_id
            payload (bytestring)

        Indicator: check self.parsed after construction to see if this packet
                   is correctly parsed. If not, probably it is not an RTMP
                   packet (e.g., a TCP ACK/FIN, ...).

        Spec: https://en.wikipedia.org/wiki/Real-Time_Messaging_Protocol.
        """
        self.chunk_header_type = None
        self.chunk_stream_id = None
        self.timestamp = None
        self.msg_length = None
        self.msg_type = None
        self.msg_stream_id = None
        self.payload = None

        self.parsed = False
        self.remain = ""

        cg = (ord(b) for b in content)
        curr_pos = 0
        try:
            # Basic header.
            basic_header = cg.next()
            curr_pos += 1
            self.chunk_header_type = basic_header >> 6
            self.chunk_stream_id = basic_header & 0b00111111
            if self.chunk_stream_id == 0:
                self.chunk_stream_id = 64 + cg.next()
                curr_pos += 1
            elif self.chunk_stream_id == 1:
                self.chunk_stream_id = 64 + ((cg.next() << 8) | cg.next())
                curr_pos += 2
            # Check chunk header type for header length.
            if self.chunk_header_type == 0b00:      # Full header.
                self.timestamp = (cg.next() << 16) | (cg.next() << 8) | cg.next()
                self.msg_length = (cg.next() << 16) | (cg.next() << 8) | cg.next()
                self.msg_type = cg.next()
                self.msg_stream_id = cg.next() | (cg.next() << 8) | \
                                     (cg.next() << 16) | (cg.next() << 24)
                curr_pos += 11
            elif self.chunk_header_type == 0b01:    # No message id.
                self.timestamp = (cg.next() << 16) | (cg.next() << 8) | cg.next()
                self.msg_length = (cg.next() << 16) | (cg.next() << 8) | cg.next()
                self.msg_type = cg.next()
                curr_pos += 7
            elif self.chunk_header_type == 0b10:    # Only timestamp.
                self.timestamp = (cg.next() << 16) | (cg.next() << 8) | cg.next()
                curr_pos += 3
            # The rest are actual payload content. If content is longer than
            # message length, the remaining might be another RTMP packet.
            self.payload = content[curr_pos:]
            if self.msg_length is not None:
                if len(self.payload) > self.msg_length + 1:
                    self.remain = self.payload[self.msg_length:]
                    self.payload = self.payload[:self.msg_length]
                    self.parsed = True
                elif len(self.payload) < self.msg_length:
                    self.parsed = False
                else:
                    self.parsed = True
            else:
                self.parsed = True
        except StopIteration:
            self.parsed = False


    def dump_fields(self):
        """
        Dump the fields for debugging.
        """
        dump = "[RTMP]"
        if self.chunk_header_type is not None:
            dump += " chunk_header_type:" + bin(self.chunk_header_type)
        if self.chunk_stream_id is not None:
            dump += " chunk_stream_id:" + str(self.chunk_stream_id)
        if self.timestamp is not None:
            dump += " timestamp:" + str(self.timestamp)
        if self.msg_length is not None:
            dump += " msg_length:" + str(self.msg_length)
        if self.msg_type is not None:
            dump += " msg_type:" + hex(self.msg_type)
        if self.msg_stream_id is not None:
            dump += " msg_stream_id:" + str(self.msg_stream_id)
        if self.payload is not None:
            dump += " payload_len:" + str(len(self.payload))
        log.debug(dump)


    # Payload keyword checkers.
    def is_play_req(self):
        return "play" in self.payload and STREAM_KEY in self.payload
    def is_play_start(self):
        return "onStatus" in self.payload and "NetStream.Play.Start" in self.payload
    def is_publish_req(self):
        return "publish" in self.payload and STREAM_KEY in self.payload
    def is_publish_start(self):
        return "onStatus" in self.payload and "NetStream.Publish.Start" in self.payload
    def is_stream_begin(self):
        return self.msg_length == 6 and \
               ((ord(self.payload[0]) << 8) | ord(self.payload[1])) == 0x0000


class LearningSwitch(object):
    """
    The learning switch "brain" associated with a single OpenFlow switch.

    When we see a packet, we'd like to output it on a port which will
    eventually lead to the destination.  To accomplish this, we build a
    table that maps addresses to ports.

    We populate the table by observing traffic.  When we see a packet
    from some source coming from some port, we know that source is out
    that port.

    When we want to forward traffic, we look up the desintation in our
    table.  If we don't know the port, we simply send the message out
    all ports except the one it came in on.  (In the presence of loops,
    this is bad!).

    In short, our algorithm looks like this:

    For each packet from the switch:
    1) Use source address and switch port to update address/port table
    2) Port for destination address in our address/port table?
        No:
            2a) Flood the packet
                DONE
    3) Is output port the same as input port?
        Yes:
            3a) Drop the packet
    4) Install flow table entry in the switch so that this flow goes out the
       appopriate port. Send the packet out appropriate port.

    RTMP packets are treated specially, in order to implement the P2P
    steering property.

    NOTE: Assuming ONLY ONE viewer currently, no multicasting.
    NOTE: CAN ONLY BE USED FOR ONE STREAM BEFORE RESTART.
    NOTE: VIEWERS MUST BE LAUNCHED BEFORE BROADCASTERS.
    """

    def __init__(self, connection):
        self.connection = connection

        self.macToPort = {}     # MAC to port table.

        # We want to hear PacketIn messages, so we listen
        # to the connection.
        connection.addListeners(self)

        #
        # RTMP-related fields.
        #

        # Role records.
        self.vport = None
        self.v_dl_addr = None
        self.v_nw_addr = None
        self.v_tp_port = None
        self.bport = None
        self.b_dl_addr = None
        self.b_nw_addr = None
        self.b_tp_port = None
        self.sport = None
        self.s_dl_addr = None
        self.s_nw_addr = None
        # s_tp_port must be RTMP_PORT.

        # Streaming status.
        self.status_vplay = False
        self.status_vready = False
        self.status_bpublish = False
        self.status_bready = False
        self.status_stream_begin = False
        self.p2p_enabled = False    # When P2P is enabled.
        self.p2p_set_off = False    # When stream begins but broadcaster unseen.

        # RTMP 12-byte strange unchunked packet buffer.
        self.prepend_buf = None


    def _handle_PacketIn_normal(self, event):
        """
        Handle packet in messages from the switch to implement the above algorithm.
        """

        packet = event.parsed
        self.macToPort[packet.src] = event.port     # 1

        def flood():
            """
            Floods the packet to all other ports.
            """
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        if packet.dst not in self.macToPort:    # 2
            flood()     # 2a
        else:
            out_port = self.macToPort[packet.dst]
            if out_port == event.port:  # 3
                log.warning("[L2] Same port for packet from %s -> %s on %s.%s."
                            "Dropping..." % (packet.src, packet.dst,
                                             dpid_to_str(event.dpid), out_port))
                return  # 3a
            # 4
            log.debug("[L2] Installing flow for %s.%i -> %s.%i" %
                      (packet.src, event.port, packet.dst, out_port))
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, event.port)
            msg.actions.append(of.ofp_action_output(port=out_port))
            msg.data = event.ofp # 6a
            self.connection.send(msg)


    def _handle_PacketIn_rtmp(self, event):
        """
        Handle RTMP packets specially. Assumes the event will parse to an
        Ethernet packet which contains an IPv4 packet which contains a TCP
        packet whose src/dst port is 1935 (meaning it contains an RTMP
        payload inside).

        NOTE: RTMP may have packets with 12 bytes sent through the link in
        advance, and the next RTMP packet should be concatenated after these
        12 bytes to reconstruct a full RTMP packet. What an annoying design!
        Debugged this for >= 10 hours :( This is even not mentioned in Adobe's
        official spec :(
        """

        packet = event.parsed
        ip_packet = packet.payload
        tcp_packet = ip_packet.payload
        self.macToPort[packet.src] = event.port
        assert tcp_packet.srcport != tcp_packet.dstport

        def normal_send():
            """
            Send the packet out in normal way w/o installing a flow table entry.
            """
            out_port = self.macToPort[packet.dst] if packet.dst in self.macToPort \
                                                  else of.OFPP_FLOOD
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=out_port))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        def dump_record():
            """
            Dump RTMP-related records for debugging.
            """
            log.debug("  vport:%s v_dl_addr:%s v_nw_addr:%s v_tp_port:%s" % \
                      (self.vport, self.v_dl_addr, self.v_nw_addr, self.v_tp_port))
            log.debug("  bport:%s b_dl_addr:%s b_nw_addr:%s b_tp_port:%s" % \
                      (self.bport, self.b_dl_addr, self.b_nw_addr, self.b_tp_port))
            log.debug("  sport:%s s_dl_addr:%s s_nw_addr:%s s_tp_port:%s" % \
                      (self.sport, self.s_dl_addr, self.s_nw_addr, RTMP_PORT))
            log.debug("  vstatus:" + str(self.status_vplay)[:1] + \
                      "-" + str(self.status_vready)[:1] +
                      "  bstatus:" + str(self.status_bpublish)[:1] + \
                      "-" + str(self.status_bready)[:1])

        #
        # Parse the RTMP pakcets. If not an actual RTMP packet (only a TCP meta
        # packet like ACK going through the RTMP port), then directly send
        # it through.
        #
        rtmp_packets = []
        content = tcp_packet.payload

        # No payload typically means a TCP ACK or something similar.
        if len(content) == 0:
            normal_send()
            return

        # Handshaking packets are typically 88 or 89 bytes in payload length.
        # Though this does not match the official spec...
        if len(content) == 88 or len(content) == 89:
            log.info("[RTMP] handshake")
            normal_send()
            return

        # Handle the strange 12-byte prepending packet.
        if len(content) == 12:
            self.prepend_buf = content
            normal_send()
            return
        elif self.prepend_buf is not None:
            content = self.prepend_buf + content
            self.prepend_buf = None

        # Parse all TCP payload data into RTMP packets.
        while len(content) > 0:
            rtmp_packet = RTMPControlPacket(content)
            rtmp_packet.dump_fields()
            if not rtmp_packet.parsed:
                normal_send()
                return
            content = rtmp_packet.remain
            rtmp_packets.append(rtmp_packet)

        #
        # For all RTMP packets in this TCP packet, parse the RTMP payload
        # for keywords. If match, record necessary info about the end hosts,
        # and update the streaming status.
        #
        assert len(rtmp_packets) > 0

        # Loop through all packets in this frame.
        for rtmp_packet in rtmp_packets:

            # Viewer -> Service, play request.
            if rtmp_packet.is_play_req():
                # Learn which port is who.
                assert tcp_packet.dstport == RTMP_PORT
                self.vport = event.port
                self.v_dl_addr = packet.src
                self.v_nw_addr = ip_packet.srcip
                self.v_tp_port = tcp_packet.srcport
                # Update status.
                self.status_vplay = True
                log.info("[RTMP] play(\'%s\')", STREAM_KEY)
                dump_record()

            # Service -> Viewer, play start message.
            if rtmp_packet.is_play_start():
                # Learn which port is who.
                assert tcp_packet.srcport == RTMP_PORT
                assert self.vport is not None
                if self.sport:
                    assert self.sport == event.port
                    assert self.s_dl_addr == packet.src
                    assert self.s_nw_addr == ip_packet.srcip
                else:
                    self.sport = event.port
                    self.s_dl_addr = packet.src
                    self.s_nw_addr = ip_packet.srcip
                # Update status.
                assert self.status_vplay
                self.status_vready = True
                log.info("[RTMP] NetStream.Play.Start")
                dump_record()

            # Broadcaster -> Service, publish request.
            if rtmp_packet.is_publish_req():
                # Learn which port is who.
                assert tcp_packet.dstport == RTMP_PORT
                self.bport = event.port
                self.b_dl_addr = packet.src
                self.b_nw_addr = ip_packet.srcip
                self.b_tp_port = tcp_packet.srcport
                # Update status.
                self.status_bpublish = True
                log.info("[RTMP] publish(\'%s\')", STREAM_KEY)
                dump_record()

            # Service -> Broadcaster, publish start message.
            if rtmp_packet.is_publish_start():
                # Learn which port is who.
                assert tcp_packet.srcport == RTMP_PORT
                assert self.bport is not None
                if self.sport:
                    assert self.sport == event.port
                    assert self.s_dl_addr == packet.src
                    assert self.s_nw_addr == ip_packet.srcip
                else:
                    self.sport = event.port
                    self.s_dl_addr = packet.src
                    self.s_nw_addr = ip_packet.srcip
                # Update status.
                assert self.status_bpublish
                self.status_bready = True
                log.info("[RTMP] NetStream.Publish.Start")
                dump_record()

            # Service -> Viewer, stream begin message.
            if rtmp_packet.is_stream_begin():
                assert tcp_packet.srcport == RTMP_PORT
                assert self.status_vready
                self.status_stream_begin = True
                log.info("[RTMP] Stream Begin 1")

        # Ensure that control packets are all sent out here.
        normal_send()

        #
        # If a stream begins but the broadcaster is unseen, it means the
        # broadcaster is not in my local network. Stop watching RTMP.
        #
        if self.status_stream_begin and not self.status_bready:
            assert self.vport is not None and \
                   self.sport is not None
            self.p2p_set_off = True
            log.info("[STREAM] P2P is set to off...")

        #
        # If is in "ready to steer state", switch to P2P mode.
        #
        if self.status_vready and self.status_bready:
            assert self.vport is not None and \
                   self.bport is not None and \
                   self.sport is not None

            #
            # Set the switch to "normal" state. Effects:
            #   1. No longer actively capturing RTMP packets.
            #   2. Capture the next packets in the notification channels and
            #      set the notification.
            #
            self.p2p_enabled = True
            log.info("[STREAM] Entering P2P stage...")

            #
            # Flow steering is not a feasible way, because the original B->S and
            # S->V connections are essentially two TCP connections. They have
            # totally different metadata like ACK#s and SEQ#s. If we simply steer
            # packets from B to V directly, then everything stops working.
            #
            # So the code below is no longer used.
            #

            # # Braodcaster -> Service steered to Broadcaster -> Viewer.
            # msg_b2v = of.ofp_flow_mod()
            # msg_b2v.match = of.ofp_match(in_port=self.bport,
            #                              dl_src=self.b_dl_addr,
            #                              dl_dst=self.s_dl_addr,
            #                              dl_type=0x0800,    # Match IPv4.
            #                              nw_src=self.b_nw_addr,
            #                              nw_dst=self.s_nw_addr,
            #                              nw_proto=6,        # Match TCP.
            #                              tp_src=self.b_tp_port,
            #                              tp_dst=RTMP_PORT)
            # msg_b2v.actions.append(of.ofp_action_dl_addr(type=of.OFPAT_SET_DL_SRC,
            #                                              dl_addr=self.s_dl_addr))
            # msg_b2v.actions.append(of.ofp_action_dl_addr(type=of.OFPAT_SET_DL_DST,
            #                                              dl_addr=self.v_dl_addr))
            # msg_b2v.actions.append(of.ofp_action_nw_addr(type=of.OFPAT_SET_NW_SRC,
            #                                              nw_addr=self.s_nw_addr))
            # msg_b2v.actions.append(of.ofp_action_nw_addr(type=of.OFPAT_SET_NW_DST,
            #                                              nw_addr=self.v_nw_addr))
            # msg_b2v.actions.append(of.ofp_action_tp_port(type=of.OFPAT_SET_TP_SRC,
            #                                              tp_port=RTMP_PORT))
            # msg_b2v.actions.append(of.ofp_action_tp_port(type=of.OFPAT_SET_TP_DST,
            #                                              tp_port=self.v_tp_port))
            # msg_b2v.actions.append(of.ofp_action_output(port=self.vport))
            # self.connection.send(msg_b2v)
            # log.info("[STREAM] Flow steering entry (Broadcaster -> Viewer) installed!")

            # # Viewer -> Service steered to Viewer -> Broadcaster.
            # msg_v2b = of.ofp_flow_mod()
            # msg_v2b.match = of.ofp_match(in_port=self.vport,
            #                              dl_src=self.v_dl_addr,
            #                              dl_dst=self.s_dl_addr,
            #                              dl_type=0x0800,    # Match IPv4.
            #                              nw_src=self.v_nw_addr,
            #                              nw_dst=self.s_nw_addr,
            #                              nw_proto=6,        # Match TCP.
            #                              tp_src=self.v_tp_port,
            #                              tp_dst=RTMP_PORT)
            # msg_v2b.actions.append(of.ofp_action_dl_addr(type=of.OFPAT_SET_DL_SRC,
            #                                              dl_addr=self.s_dl_addr))
            # msg_v2b.actions.append(of.ofp_action_dl_addr(type=of.OFPAT_SET_DL_DST,
            #                                              dl_addr=self.b_dl_addr))
            # msg_v2b.actions.append(of.ofp_action_nw_addr(type=of.OFPAT_SET_NW_SRC,
            #                                              nw_addr=self.s_nw_addr))
            # msg_v2b.actions.append(of.ofp_action_nw_addr(type=of.OFPAT_SET_NW_DST,
            #                                              nw_addr=self.b_nw_addr))
            # msg_v2b.actions.append(of.ofp_action_tp_port(type=of.OFPAT_SET_TP_SRC,
            #                                              tp_port=RTMP_PORT))
            # msg_v2b.actions.append(of.ofp_action_tp_port(type=of.OFPAT_SET_TP_DST,
            #                                              tp_port=self.b_tp_port))
            # msg_v2b.actions.append(of.ofp_action_output(port=self.bport))
            # self.connection.send(msg_v2b)
            # log.info("[STREAM] Flow steering entry (Viewer -> Broadcaster) installed!")

            # # Packets from the service node will be dropped.
            # # msg_cdn = of.ofp_flow_mod()
            # # msg_cdn.match = of.ofp_match(in_port=self.sport,
            # #                              dl_src=self.s_dl_addr,
            # #                              dl_type=0x0800,    # Match IPv4.
            # #                              nw_src=self.s_nw_addr,
            # #                              nw_proto=6,        # Match TCP.
            # #                              tp_src=RTMP_PORT)
            # # self.connection.send(msg_cdn)   # No action means dropping.
            # # log.info("[STERAM] Service packets dropping entry installed!")

            # # AFTER the installation, there should be no more RTMP packets sent to
            # # this controller!


    def _handle_PacketIn_notify(self, event):
        """
        Handle P2P notification channel packets.
        """

        packet = event.parsed
        ip_packet = packet.payload
        tcp_packet = ip_packet.payload
        self.macToPort[packet.src] = event.port
        assert tcp_packet.srcport != tcp_packet.dstport

        def normal_send():
            """
            Send the packet out in normal way w/o installing a flow table entry.
            """
            out_port = self.macToPort[packet.dst] if packet.dst in self.macToPort \
                                                  else of.OFPP_FLOOD
            msg = of.ofp_packet_out()
            msg.actions.append(of.ofp_action_output(port=out_port))
            msg.data = event.ofp
            msg.in_port = event.port
            self.connection.send(msg)

        log.debug("<NOTIFY> heartbeat %s -> %s" % (ip_packet.srcip, ip_packet.dstip))

        #
        # If P2P stage is enabled, hack through this notification packet and modify
        # its payload to the destination's peer's IP address.
        #
        if self.p2p_enabled and tcp_packet.srcport == NOTIFY_PORT:
            assert self.vport is not None and \
                   self.bport is not None and \
                   self.sport is not None
            assert ip_packet.srcip == self.s_nw_addr

            msg_out = of.ofp_packet_out()
            out_port = self.macToPort[packet.dst] if packet.dst in self.macToPort \
                                                  else of.OFPP_FLOOD
            msg_out.actions.append(of.ofp_action_output(port=out_port))

            # Rewrite TCP payload to the peer's IP address.
            new_payload = None
            if ip_packet.dstip == self.v_nw_addr:   # If destination is viewer.
                new_payload = ("{0:"+HEARTBEAT_PADDING+"<"+str(HEARTBEAT_LENGTH)+"}") \
                              .format(str(self.b_nw_addr))
            if ip_packet.dstip == self.b_nw_addr:   # If destination is broadcaster.
                new_payload = ("{0:"+HEARTBEAT_PADDING+"<"+str(HEARTBEAT_LENGTH)+"}") \
                              .format(str(self.v_nw_addr))
            tcp_packet.set_payload(new_payload)

            msg_out.data = packet
            msg_out.in_port = event.port
            self.connection.send(msg_out)
            log.info("<NOTIFY> Pushed \'%s\'' to %s" % (new_payload, ip_packet.dstip))

            # Install a drop entry for further notification heartbeats.
            msg_mod = of.ofp_flow_mod()
            msg_mod.match = of.ofp_match.from_packet(packet, event.port)
            self.connection.send(msg_mod)
            log.info("<NOTIFY> Drop entry installed!")

        else:
            normal_send()


    def _handle_PacketIn(self, event):
        """
        POX handler for an OpenFlow PacketIn event.
        RTMP packets are recognized through the RTMP service port (default = 1935).
        Notifications are recognized through the notification port (now = 42857).
        """
        tcp_packet = event.parsed.find('tcp')

        # Once P2P is enabled/set-off, all RTMP packets will go through _handle_normal,
        # which leads to a flow table entry to be installed. Thus, RTMP video chunks
        # will not go through this controller.
        if not self.p2p_enabled and not self.p2p_set_off and tcp_packet and \
           (tcp_packet.srcport == RTMP_PORT or tcp_packet.dstport == RTMP_PORT):
            self._handle_PacketIn_rtmp(event)

        # Notifications channel is very lightweighted so the overhead neglectable.
        elif tcp_packet and \
             (tcp_packet.srcport == NOTIFY_PORT or tcp_packet.dstport == NOTIFY_PORT):
            self._handle_PacketIn_notify(event)
        
        # This branch leads to a flow table entry to be installed.
        else:
            self._handle_PacketIn_normal(event)


class BypassLivestreaming(object):
    """
    Waits for OpenFlow switches to connect and makes them learning switches.
    """
    def __init__(self):
        core.openflow.addListeners(self)

    def _handle_ConnectionUp(self, event):
        log.debug("Connection %s" % (event.connection,))
        LearningSwitch(event.connection)


def launch():
    """
    Main entrance of this component.
    """
    core.registerNew(BypassLivestreaming)
