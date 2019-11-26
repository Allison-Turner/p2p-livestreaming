#! /usr/bin/python


import random


FRAME_RATE = 10
FRAME_SIZE = 144*120


# Video simulated as a list of bytearrays, each representing a frame.
video = [bytearray(random.getrandbits(8) for _ in xrange(FRAME_SIZE))
         for _ in xrange(FRAME_RATE*12)]    # 12s video.

with open("video.data", 'wb') as fvideo:
    for frame in video:
        fvideo.write(frame)
