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
fig_size = [fig_with,fig_height]

params = {'backend': 'ps',
    'axes.labelsize': 22,
    'text.fontsize': 22,
    'legend.fontsize': 20,
    'xtick.labelsize': 20,
    'ytick.labelsize': 20,
    'font.size': 20,
    'figure.figsize': fig_size,
    'font.family': 'Times New Roman'}


db_name = "longrun.db"
db_table_name = "longrun"


query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name)

query_range_for_experiment = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.machine_id=?
                                AND TABLE.round_id>=?
                                AND TABLE.round_id<? ORDER BY TABLE.round_id'''.replace("TABLE", db_table_name)
agr_interval = 60
start_id = 300 - agr_interval
end_id = 3900
steps = (end_id-start_id)/agr_interval

conn = sqlite3.connect(db_name)

c = conn.cursor()
ma_id = [x[0] for x in c.execute(query_maid).fetchall()]
res = [[0,0,0,0,0]]

min = 0
add_min = agr_interval/60

res = []
for cur_start in range(start_id+1, end_id+1, agr_interval):
    machine_res = []
    for maid in ma_id:
        data = np.asarray(c.execute(query_range_for_experiment, (maid, cur_start, cur_start+agr_interval)).fetchall())
        data[:, 2] = np.square(data[:, 2])
        sump_tps = np.sum(data[:, 0])
        avg_resp = np.average(data, axis=0)
        machine_res.append([sump_tps, avg_resp[1], avg_resp[2]])
    tp = 0
    for temp in machine_res:
        tp += temp[0]
    machine_res = np.average(np.asarray(machine_res), axis=0)
    machine_res[0] = tp
    res.append(np.append([min], machine_res))
    min += add_min
res = np.asarray(res)
res[:, 3] = np.sqrt(res[:, 3])

plt.rcParams.update(params)
plt.rc('pdf', fonttype=42)


plt.plot(res[:, 0], res[:, 1]/60, '-o')
plt.title("Stability Experiment: Aggregated throughput", y=1.02)
plt.ylabel("# operations per second [ops/s]")
plt.xlabel("time in minutes")
plt.grid(color='gray', linestyle='dashed')
plt.ylim([0,18000])

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/throughput_longrun.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()

err_plus = res[:, 2] + res[:, 3]
err_minus = res[:, 2] - res[:, 3]
line, = plt.plot(res[:, 0], res[:, 2]/1000, '-o')
plt.title("Stability Experiment: Average response time", y=1.02)
plt.ylabel("time in milliseconds [ms]")
plt.xlabel("time in minutes")
plt.grid(color='gray', linestyle='dashed')
plt.fill_between(res[:, 0], err_minus/1000, err_plus/1000,
    alpha=0.2, facecolor='r')
plt.plot(res[:, 0], err_minus/1000, '-o', color='r')
err, = plt.plot(res[:, 0], err_plus/1000, '-o', color='r')

plt.legend([line, err], ['avg response time', 'standard deviation'], loc=2)

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/responsetime_longrun.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()