import memaslap_extractor as extractor
import math
import numpy as np
import os
import re
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

golden_mean = ((math.sqrt(5)-1.0)/2.0)*0.8
fig_with_pt = 600
inches_per_pt = 1.0/72.27*2
fig_with = fig_with_pt*inches_per_pt
fig_height = fig_with * golden_mean
fig_size = [fig_with, fig_height]

params = {'backend': 'ps',
    'axes.labelsize': 22,
    'text.fontsize': 22,
    'legend.fontsize': 20,
    'xtick.labelsize': 20,
    'ytick.labelsize': 20,
    'font.size': 20,
    'figure.figsize': fig_size,
    'font.family': 'Times New Roman'}

f = open("mean_alysis_resp.csv", 'r')
resp = []
resp.append(0.0)
for line in f:
    resp.append(float(line))
resp = np.asarray(resp)
f.close()

f1 = open("mean_analysis_tp.csv", 'r')
tp = []
tp.append(0.0)
for line in f1:
    tp.append(float(line))
tp = np.asarray(tp)
f1.close()

plt.rcParams.update(params)
plt.rc('pdf', fonttype=42)

f, (ax1, ax2) = plt.subplots(1, 2)
N = np.asarray(range(0,len(tp)))
ax1.plot(N[::10], tp[::10], '-o')
ax1.set_ylabel("operations per second [ops/s]")
ax2.plot(N[1::10], resp[1::10], '-o')
ax2.set_ylabel("response time [ms]")

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('./network_model.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()