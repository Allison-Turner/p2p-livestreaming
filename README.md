# P2P Livestreaming

Allison Turner, Guanzhou Hu, and Vishrant Tripathi's workspace for 6.829 fall '19 final project on peer-to-peer optimizations to livestreaming.

## Research Goal

We consider a single content-generating user and many content-consuming users on a livestreaming platform such as Periscope or Twitch. Many such livestreaming platforms are growing fast, and find that as their product must scale with growing audiences, minimizing latency for as many audience members as possible is a persistent issue. Most platforms utilize CDNs [1] in order to address these competing issues, but inefficiencies persist in these designs. Our goal is to design a more efficient peer-to-peer broadcasting methodology for livestreaming platforms.

## Methodology

We hope to devise a protocol-based method for “crowd-sourcing content distribution”. We want to eliminate unnecessary routing times between users and platform CDNs. Users could be more geologically proximate to each other in the network than they would be to a CDN data center, and we want to use this fact to pass the information along in a peer-to-peer fashion. Leveraging this network proximity of audience members could reduce latency. The peer-to-peer nature of our methodology will make this design highly scalable. Latency will be our measurement of the success of our design. The closer that the delay of each chunk of streaming data is to RTTmin, the better the user’s experience will be as a broadcaster or an audience member, and the more likely they are to be engaged with the livestream.

## Tools

* Topology simulated on [Mininet](https://github.com/mininet/mininet/wiki/Introduction-to-Mininet)
* Mock livestreaming application created with [OBS](https://obsproject.com/)

## References
1. B. Wang, X. Zhang, G. Wang, H. Zheng, and B. Zhao, “Anatomy of a Personalized Livestreaming System” in Proc. IMC 2016, November 14-16, 2016, Santa Monica, CA, USA.

## TODO List

- [x] Prototyping (proof-of-concpet results, see README under `prototype/` folder)
- [ ] ...
