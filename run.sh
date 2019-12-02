#!/bin/bash

#
# Usage: sudo ./src/run.sh
#
# Runs the experiments and generate the delay plot. Check the generated plot
# at 'results/delay-plot.png'.
#


function header {
    echo -e "\e[1;33m$1\e[0m"
}


# Run direct.
header "Running original settings..."
./src/pox/pox.py livestreaming.direct > /dev/null 2>&1 &
sleep 3     # Ensure POX is up.
sudo python src/live.py videos/30fps-600frames.flv output/viewed.flv
sudo kill $(pgrep -f pox.py)
cp output/b2s.ping results/direct-b2s.ping
cp output/s2v-10.0.0.3.ping results/direct-s2v.ping


# Run bypass.
header "Running original settings..."
./src/pox/pox.py livestreaming.bypass > /dev/null 2>&1 &
sleep 3     # Ensure POX is up.
sudo python src/live.py videos/30fps-600frames.flv output/viewed.flv
sudo kill $(pgrep -f pox.py)
cp output/b2v-10.0.0.3.ping results/bypass-b2v.ping


# Generate the plot.
header "Generating the delay plot..."
python src/plot.py
