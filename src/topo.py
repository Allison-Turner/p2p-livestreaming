#! /usr/bin/python


from mininet.topo import Topo


class LivestreamingSingleTopo(Topo):
    """
    Livestreaming single L2-switch topology:

                            hs (CDN)
                             |
                             | 2Mbps, 300ms
                             |
        hb (broadcaster) --> s1 --> hv (nearby viewer(s))
               10Mbps, 30ms  :
                            c0 (OF controller)

    One broadcaster (h1). Number of viewers can be specified (default is 1).
    """

    def build(self, num_viewers=1):
        """
        Override this func to create customized topo.
        """
        s1 = self.addSwitch('s1')
        hb = self.addHost('hb')
        hs = self.addHost('hs')
        hvs = [self.addHost('hv'+str(i)) for i in range(1, num_viewers+1)]

        lan_link_opts = dict(bw=10, delay='30ms')
        cdn_link_opts = dict(bw=2, delay='300ms')
        self.addLink(hb, s1, **lan_link_opts)
        for hv in hvs:
            self.addLink(hv, s1, **lan_link_opts)
        self.addLink(s1, hs, **cdn_link_opts)


class LivestreamingMultiTopo(Topo):
    """
    TODO...
    """

    def build(self):
        pass


# Add to `topos` dict to make it visible to CLI.
# Usage: `sudo mn --custom src/topo.py --topo <Name>[,Param] --link=tc --mac
#         --controller remote --switch ovsk`.
topos = {'livestreaming_single': (lambda n=1: LivestreamingSingleTopo(num_viewers=n)),
         'livestreaming_multi':  (lambda: LivestreamingMultiTopo())}
