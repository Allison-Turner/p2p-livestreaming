# Common shared constants.


import struct
import time


# Video info.
FRAME_RATE = 10
FRAME_SIZE = 144*120


# Control messages.
FRAME_BEG = bytearray(struct.pack('!b', 1))
FRAME_END = bytearray(struct.pack('!b', 2))
BCAST_BEG = bytearray(struct.pack('!b', 3))
BCAST_END = bytearray(struct.pack('!b', 4))
CTRL_MSG_LEN = 1


# Header info.
TIMESTAMP_LEN = 8


# Time utilities.
def get_timestamp():
    return bytearray(struct.pack('!d', time.time()))

def parse_timestamp(stamp):
    return struct.unpack('!d', stamp)[0]
