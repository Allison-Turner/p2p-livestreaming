# Common shared constants.


import os
import sys


# Hardcoding RTMP constants.
RTMP_PORT = 1935
STREAM_KEY = "6829proj"


# P2P notification constants & utilities.
NOTIFY_PORT = 42857     # Port opening for P2P notification channel.
HEARTBEAT_CLUE = "heartbeat"
HEARTBEAT_DATA = "xxx" + HEARTBEAT_CLUE + "xxx"     # Max IP length is 15 bytes.
HEARTBEAT_LENGTH = 15
HEARTBEAT_PADDING = '|'
PEER_PORT = 2000

def notify_is_heartbeat(notify_data):
    return HEARTBEAT_CLUE in notify_data

def parse_notify_ip(notify_data):
    return notify_data[:notify_data.find(HEARTBEAT_PADDING)]


ROOT_DIR = os.path.abspath(os.path.dirname(sys.argv[0])) + "/../.."
OUTPUT_DIR = ROOT_DIR + "/output"
