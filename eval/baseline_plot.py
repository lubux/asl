import memaslap_extractor as extractor
import math
import numpy as np
import os
import re
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager

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


db_name = "baseline.db"
db_table_name = "baseline"

query_clients = '''SELECT TABLE.num_clients
                   FROM TABLE
                   GROUP BY TABLE.num_clients
                   ORDER BY TABLE.num_clients'''.replace("TABLE", db_table_name)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name)

query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name)

query_range_for_experiment = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_clients=?
                                AND TABLE.machine_id=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?'''.replace("TABLE", db_table_name)

if not os.path.isfile("./"+db_name):
    extractor.move_client_data_to_db("../data/baseline/", db_name, db_table_name)

conn = sqlite3.connect(db_name)

c = conn.cursor()
exp_id = [x[0] for x in c.execute(query_expid).fetchall()]
ma_id = [x[0] for x in c.execute(query_maid).fetchall()]
res = [[0,0,0,0,0]]
for num_client_tuple in c.execute(query_clients).fetchall():
    num_client = num_client_tuple[0]
    exp_res = []
    for id in exp_id:
        machine_res = []
        for maid in ma_id:
            data = np.asarray(c.execute(query_range_for_experiment, (id, num_client, maid, 15, 45)).fetchall())
            data[:, 2] = np.square(data[:, 2])
            avg = np.average(data, axis=0)
            std = np.std(data, axis=0)
            machine_res.append([avg[0], std[0], avg[1], avg[2]])
        tp = 0
        for temp in machine_res:
            tp += temp[0]
        machine_res = np.average(np.asarray(machine_res), axis=0)
        machine_res[0] = tp
        exp_res.append(machine_res)
    exp_res = np.average(np.asarray(exp_res), axis=0)
    res.append(np.append([num_client*len(ma_id)], exp_res))
res = np.asarray(res)
res[:, 4] = np.sqrt(res[:, 4])

plt.rcParams.update(params)
plt.rc('pdf',fonttype = 42)


plt.errorbar(res[:, 0], res[:, 1], yerr=res[:, 2],fmt='-o', ecolor='r')
plt.title("Memcache Baseline: Aggregated throughput", y=1.02)
plt.ylabel("# operations per second [ops/s]")
plt.xlabel("number of clients")
plt.grid(color='gray', linestyle='dashed')

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/throughput_baseline.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()

err_plus = res[:, 3] + res[:, 4]
err_minus = res[:, 3] - res[:, 4]
line, = plt.plot(res[:, 0], res[:, 3]/1000, '-o', lw=2)
plt.title("Memcache Baseline: Response time", y=1.02)
plt.ylabel("time in milliseconds [ms]")
plt.xlabel("number of clients")
plt.grid(color='gray', linestyle='dashed')
plt.fill_between(res[:, 0], err_minus/1000, err_plus/1000,
    alpha=0.2, facecolor='r')
plt.plot(res[:, 0], err_minus/1000, '-o', color='r')
err, = plt.plot(res[:, 0], err_plus/1000, '-o', color='r')
plt.xlim([0, 130])

plt.legend([line, err], ['avg response time', 'standard deviation'], loc=2)

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/responsetime_baseline.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()