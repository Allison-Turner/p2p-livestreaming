# Proof-of-Concept Prototype

Guanzhou Hu (josehu@mit.edu)


## Design

Prototype using Mininet + Python sockets toolchain, with the following minimal topology as a proof-of-concept:

```text
                    h3 (CDN)
                     |
                     | 2Mbps, 100ms
                     |
h1 (broadcaster) --> s1 --> h2 (nearby viewer)
       10Mbps, 30ms  :
                    c0 (OF controller)
```

- *Original*: h1 -> s1 -> h3 (CDN), then h3 send the frame down to h2
- *Bypassed*: h1 -> s1, controller sees our protocol and pushes the frame from s1 -> h2 directly
    - Currently we are just sending from h1 -> h2 directly, w/o the interference of OpenFlow


## How to Run

Go under the `prototype/` folder.

Use `utils/gen-video.py` to generate a sample video file. Put the video file `video.data` under `prototype/` folder. Frame rate and frame size can be adjusted in the gen script, but make sure to modify `hosts/common.py` so that the parameters match. ("Video" here is simply an uncompressed list of random bytearrays as frames, so can be very huge for higher quality parameters.)

Then, under the `prototype/` folder, do:

```bash
$ sudo python live.py
```

The three hosts: *broadcaster*, *viewer*, and *CDN server*, each runs the corresponding app under `hosts/` folder. They are built directly upon the sockets API to simulate a video livestreaming application.

Detailed output logs can be found under `output/` folder after running the test.


# Results

Experiment results on Ubuntu 18.04 VM, w/ the above topology and w/o CPU-limited hosts:

```text
### Topology ###
h1 h1-eth0:s1-eth1
h2 h2-eth0:s1-eth2
h3 h3-eth0:s1-eth3
### Ping all ###
*** Ping: testing ping reachability
h1 -> h2 h3
h2 -> h1 h3
h3 -> h1 h2
*** Results: 0% dropped (6/6 received)
### Testing: original ###
Avg. latency: 301 ms.
### Testing: bypassed ###
Avg. latency: 145 ms.
```

This verifies our design as expected ;)
