# Proof-of-Concept Prototype

Prototype using Mininet + OpenFlow + (maybe OBS) toolchain, with the following minimal topology as a proof-of-concept:

```
                        h3 (CDN)
                         |
                         | 2Mbps, 30ms
                         |
    h1 (broadcaster) --> s1 --> h2 (nearby viewer)
           10Mbps, 5ms   :
                        c0 (OF controller)
```

- *Original*: h1 -> s1 -> h3 (CDN), then h2 polls periodically from h3 and get a frame
- *Bypassed*: h1 -> s1, controller sees our protocol and pushes the frame from s1 -> h2 directly
