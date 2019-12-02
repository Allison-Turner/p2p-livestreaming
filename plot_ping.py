'''
Plot ping RTTs over time
'''
from helper import *
import plot_defaults, argparse
#from xlrd import col
import numpy

from matplotlib.ticker import MaxNLocator
from pylab import figure
import matplotlib as m
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument('--files',
                    '-f',
                    help="Ping output files to plot",
                    required=True,
                    action="store",
                    nargs='+')

parser.add_argument('--freq',
                    help="Frequency of pings (per second)",
                    type=int,
                    default=10)

parser.add_argument('--out',
                    '-o',
                    help="Output png file for the plot.",
                    default=None)  # Will show the plot

args = parser.parse_args()


def parse_ping(fname):
  retx = []
  rety = []
  lines = open(fname).readlines()
  num = 0
  for line in lines:
    if 'bytes from' not in line:
      continue
    try:
      rtt = line.split(' ')[-2]
      rtt = rtt.split('=')[1]
      rtt = float(rtt)
      retx.append(num)
      rety.append(rtt)
      #ret[num,0] = num
      #ret[num,1] = rtt
      num += 1
    except:
      break
  return retx, rety


m.rc('figure', figsize=(16, 6))
fig = figure()
ax = fig.add_subplot(111)
for i, f in enumerate(args.files):
  datax, datay = parse_ping(f)
  #print numpy.asarray(datay)
  xaxis = numpy.asarray(datax)#map(float, col(0, data))
  start_time = xaxis[0]
  xaxis = map(lambda x: (x - start_time) / args.freq, xaxis)
  qlens = numpy.asarray(datay)

  ax.plot(xaxis, qlens, lw=2)
  ax.xaxis.set_major_locator(MaxNLocator(4))

plt.ylabel("RTT (ms)")
plt.grid(True)

if args.out:
  plt.savefig(args.out)
else:
  plt.show()
