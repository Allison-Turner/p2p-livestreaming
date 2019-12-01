# P2P Livestreaming

![languages](https://img.shields.io/github/languages/count/Allison-Turner/p2p-livestreaming?color=gold)
![top-lang](https://img.shields.io/github/languages/top/Allison-Turner/p2p-livestreaming)
![code-size](https://img.shields.io/github/languages/code-size/Allison-Turner/p2p-livestreaming?color=green)

Allison Turner, Guanzhou Hu, and Vishrant Tripathi's workspace for 6.829 fall '19 final project on peer-to-peer optimizations to livestreaming.


## TODO List

- [x] Prototyping (proof-of-concpet results, see README under `prototype/` folder)
- [ ] OpenFlow controller logic
- [x] Host applications (`ffmpeg` on broadcaster + web server on CDN node + `rtmp` utils on viewers)
- [ ] OBS support & testing (needs a Ubuntu Desktop machine...)
- [ ] ...


## Preparations

With the provided `Vagrantfile`, launch and log into the VM by:

```bash
$ vagrant up
$ vagrant ssh
```

And install the following dependencies:

- `devscripts`, `moreutils`, `expect` by `apt`
- [Mininet 2.0 full ver.](http://mininet.org/): Follow the "Get Started" Page - Option 2 and install everything
- [Nginx & RTMP module](https://opensource.com/article/19/1/basic-live-video-streaming-server): Follow the post for how to install and setup Nginx to serve as an RTMP livestreaming server
- [FFmpeg](https://trac.ffmpeg.org/wiki/StreamingGuide) by `sudo apt install ffmpeg`: A command-line-compatible multi-media tool. It supports streaming a pre-recorded video file to some server (A workaround for not being able to use OBS within VMs)
- `rtmpdump` by `apt`: A command-line tool to pull an RTMP stream. It serves as a viewer
- `mplayer` by `apt`: Same as above

> Using OBS for real-time demonstration is not included yet. OBS cannot work within a Ubuntu server VM because it requires a graphic card access even if we only want to stream a pre-recorded video file. Meanwhile, all the OpenFlow networking experiments must run with Mininet, requiring a VM.
>
> At presentation it would be the best if we can prepare a Ubuntu Desktop machine with all the Mininet stuff installed and working correctly. Then we can use the Linux version of OBS to perform the real-time desktop capturing demonstration.


## How to Run

The following is now only a sample run walkthrough, using a traditional L2 learning switch w/o P2P optimizations.

1. Log into the Vagrant VM. You should be at the `/livestreaming` path.
    - Make at least 2 terminal windows here
    - Make sure X11 is working correctly
2. `$ sudo wireshark &` to launch WireShark. Keep WireShark window at side.
    - In WireShark, capture with filter *any*
    - Then, set display filter as required
3. `$ ./src/pox/pox.py livestreaming.bypass` to launch our POX controller
4. `$ sudo python src/live.py videos/30fps-600frames.flv output/viewed.flv` in another terminal to run the test


## Manual Commands Memo

#### WireShark

```bash
# Launching in background (Make sure X11 is working correctly).
$ sudo wireshark &

# Capture filter = *any*
# Display filter = rtmpt || (openflow_v1 && ip.addr==10.0.0.0/24)
```

#### POX Controller

```bash
# Launching.
$ ./src/pox/pox.py livestreaming.<direct|bypass> [log.level --DEBUG]
```

#### Mininet

```bash
# Launching.
$ sudo mn --custom src/topo.py --topo livestreaming_<single|multi>[,param] --link=tc --mac --controller remote --switch ovsk

# Individual X terminals.
mininet> xterms hb hs hv1 hv2

# Cleaning up.
$ sudo mn -c
```

#### Streaming Utilities

```bash
# FFmpeg: Streaming a .flv file to an Nginx RTMP server, with key = 6829proj.
$ ffmpeg -re -i <filename>.flv -flvflags no_duration_filesize -max_muxing_queue_size 8192 -f flv rtmp://<server_address>/live/6829proj

# FFmpeg: P2P RTMP streaming broadcaster.
$ ffmpeg -re -i <filename>.flv -flvflags no_duration_filesize -max_muxing_queue_size 8192 -f flv tcp://<client_address>:<port>

# RTMPdump: Pulling the above RTMP stream from the server and save into a file.
$ rtmpdump -r rtmp://<server_address>/live/6829proj -o <savename>.flv

# MPlayer: Pulling an RTMP stream to view.
$ mplayer -nocorrect-pts -nocache -nosound -vo null -noidle [-frames <num_frames>] -dumpstream -dumpfile <dump_file> rtmp://<server_address>/live/6829proj

# MPlayer: P2P RTMP streaming client.
$ mplayer -nocorrect-pts -nocache -nosound -vo null -noidle [-frames <num_frames>] -dumpstream -dumpfile <dump_file> ffmpeg://tcp://<my_ip>:<port>?listen
```

NOTE: `mplayer` will always miss 12 frames no matter under which frame rate (don't know why), so for a 300 frames video, set the player to pull 288 frames and it will terminate correctly.

#### Video Tools

```bash
# FFmpeg: Check fps & exact number of frames in a video.
ffmpeg -i <filename>.flv -map 0:v:0 -c copy -f null -

# FFmpeg: Remove audio track, filter with certain fps, and crop at exact number of frames.
ffmpeg -i <in_file>.flv -an -filter:v fps=fps=<target_fps> -frames <num_frames> <out_file>.flv
```
