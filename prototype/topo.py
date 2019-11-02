#! /usr/bin/python


from mininet.topo import Topo


class LivestreamingTopo(Topo):
    """
    Livestreaming prototype topology:

                            h3 (CDN)
                             |
                             | 2Mbps, 30ms
                             |
        h1 (broadcaster) --> s1 --> h2 (nearby viewer)
               10Mbps, 5ms   :
                            c0 (OF controller)
    """

    def build(self):
        """
        Override this func to create customized topo.
        """
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')

        lan_link_opts = dict(bw=10, delay='5ms')
        cdn_link_opts = dict(bw=2, delay='30ms')
        self.addLink(h1, s1, **lan_link_opts)
        self.addLink(h2, s1, **lan_link_opts)
        self.addLink(s1, h3, **cdn_link_opts)


# Add to `topos` dict to make it visible to CLI.
# Usage: `sudo mn --custom prototype/topo.py --topo livestreaming --link=tc`.
topos = {'livestreaming': (lambda: LivestreamingTopo())}
