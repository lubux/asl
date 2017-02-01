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

db_name = "maxtpexp.db"
db_table_name_client = "maxtpexp_c"
db_table_name_mw = "maxtpexp_mw"

query_clients = '''SELECT TABLE.num_clients
                   FROM TABLE
                   GROUP BY TABLE.num_clients
                   ORDER BY TABLE.num_clients'''.replace("TABLE", db_table_name_client)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 WHERE TABLE.num_threads=? AND TABLE.num_clients=?
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name_client)

query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name_client)

query_numthreads = '''SELECT TABLE.num_threads
                FROM TABLE
                GROUP BY TABLE.num_threads
                ORDER BY TABLE.num_threads'''.replace("TABLE", db_table_name_client)

query_range_for_experiment = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_clients=?
                                AND TABLE.machine_id=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.num_threads=? AND NOT TABLE.std is null'''.replace("TABLE", db_table_name_client)

conn = sqlite3.connect(db_name)
c = conn.cursor()
ma_id = [x[0] for x in c.execute(query_maid).fetchall()]
num_threads_list = [x[0] for x in c.execute(query_numthreads).fetchall()]
results_per_thread = []

for num_threads in num_threads_list:
    res = [[0, 0, 0, 0, 0]]
    for num_client_tuple in c.execute(query_clients).fetchall():
        num_client = num_client_tuple[0]
        exp_res = []
        exp_id = [x[0] for x in c.execute(query_expid, (num_threads, num_client)).fetchall()]
        if len(exp_id) < 1:
            np.append([num_client * 5], np.asarray([0 for x in range(4)]))
            continue
        for id in exp_id:
            machine_res = []
            for maid in ma_id:
                data_tem = c.execute(query_range_for_experiment, (id, num_client, maid, 10, 120, num_threads)).fetchall()
                if len(data_tem) == 0:
                    continue
                data = np.asarray(data_tem)
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
    results_per_thread.append([num_threads, res])

plt.rcParams.update(params)
plt.rc('pdf',fonttype = 42)

lines = []
names = []
for plotdata in results_per_thread:
    res = plotdata[1]
    cur = plt.errorbar(res[:, 0], res[:, 1], yerr=res[:, 2],fmt='-o', ecolor='r')
    lines.append(cur)
    names.append('%d Threads' % plotdata[0])

plt.legend(lines, names, loc=2)
plt.title("Max Throughput Experiment: Aggregated throughput", y=1.02)
plt.ylabel("# operations per second [ops/s]")
plt.xlabel("number of clients")
plt.grid(color='gray', linestyle='dashed')

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/maxtp_throughput_4.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()
