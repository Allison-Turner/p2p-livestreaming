# P2P Livestreaming

![languages](https://img.shields.io/github/languages/count/Allison-Turner/p2p-livestreaming?color=gold)
![top-lang](https://img.shields.io/github/languages/top/Allison-Turner/p2p-livestreaming)
![code-size](https://img.shields.io/github/languages/code-size/Allison-Turner/p2p-livestreaming?color=green)

Allison Turner, Guanzhou Hu, and Vishrant Tripathi's workspace for 6.829 fall '19 final project on peer-to-peer optimizations to livestreaming.

Presentation slides: [CLICK HERE](https://docs.google.com/presentation/d/1DvFXPU94F932dR3AAu87u9xZMteHArnPzpD0hii22aU/edit).


## Description

#### Research Goal

We consider a single content-generating user and many content-consuming users on a livestreaming platform such as Periscope or Twitch. Many such livestreaming platforms are growing fast, and find that as their product must scale with growing audiences, minimizing latency for as many audience members as possible is a persistent issue. Most platforms utilize CDNs [1] in order to address these competing issues, but inefficiencies persist in these designs. Our goal is to design a more efficient peer-to-peer broadcasting methodology for livestreaming platforms.

#### Methodology

We hope to devise a protocol-based method for “crowd-sourcing content distribution”. We want to eliminate unnecessary routing times between users and platform CDNs. Users could be more geologically proximate to each other in the network than they would be to a CDN data center, and we want to use this fact to pass the information along in a peer-to-peer fashion. Leveraging this network proximity of audience members could reduce latency. The peer-to-peer nature of our methodology will make this design highly scalable. Latency will be our measurement of the success of our design. The closer that the delay of each chunk of streaming data is to RTTmin, the better the user’s experience will be as a broadcaster or an audience member, and the more likely they are to be engaged with the livestream.

#### References
1. B. Wang, X. Zhang, G. Wang, H. Zheng, and B. Zhao, “Anatomy of a Personalized Livestreaming System” in Proc. IMC 2016, November 14-16, 2016, Santa Monica, CA, USA.


## TODO List

- [x] Prototyping (proof-of-concpet results, see README under `prototype/` folder)
- [x] OpenFlow controller logic
- [x] Host applications (`ffmpeg` on broadcaster + web server on CDN node + `rtmp` utils on viewers)
- [ ] OBS/FFmpeg/MPlayer graphics support & testing (needs a Ubuntu Desktop machine...)
- [ ] Comprehensive experiment results
- [ ] Report & presentation materials


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
- `mplayer` by `apt`: Same as above but much more powerful

> Using OBS for real-time demonstration is not included yet. OBS cannot work within a Ubuntu server VM because it requires a graphic card access even if we only want to stream a pre-recorded video file.


## How to Run

Simply do:

```bash
$ sudo ./run.sh     # This will run an experiment and generate a delay plot.
```

Check the generated delay plot at `results/delay-plot.png`.

Key files in this project include:

```text
/src/
  |- live.py    # Aggregated experiment script
  |- topo.py    # Mininet custom topology for our settings
  |- hosts/*    # Livestreaming end host apps: CDN, broadcaster, viewer
  |- pox/pox/livestreaming/*    # OpenFlow switches logic
```


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
