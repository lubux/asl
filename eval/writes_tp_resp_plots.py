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

def compute_resp(data_in, percentil):
    num_actions = data_in[0]
    data = [int(x) for x in data_in[1].split(",")]
    del data[0]
    pow = 4
    sum = 0.0
    for cur in data:
        sum += cur
        cur_precent = sum/float(num_actions)
        print cur_precent
        if cur_precent>=percentil:
            print ((2**pow))
            return ((2**pow))
        pow += 1

params = {'backend': 'ps',
    'axes.labelsize': 22,
    'legend.fontsize': 20,
    'xtick.labelsize': 20,
    'ytick.labelsize': 20,
    'font.size': 20,
    'figure.figsize': fig_size,
    'font.family': 'Times New Roman'}

db_name = "writesexp_exp.db"
db_table_name_client = "writesexp_c"
db_table_name_mw = "writesexp_mw"
table_name_resp = "writesexp_resp"

query_num_servers = '''SELECT TABLE.num_servers
                       FROM TABLE
                      GROUP BY TABLE.num_servers
                      ORDER BY TABLE.num_servers'''.replace("TABLE", db_table_name_client)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 WHERE TABLE.num_servers=? AND TABLE.replication=? AND TABLE.workload_id=?
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name_client)

query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name_client)


query_range_for_experiment = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.machine_id=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.workload_id=?
                                AND TABLE.replication=? AND NOT TABLE.std is null'''.replace("TABLE", db_table_name_client)

query_max_round_ID = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.workload_id=?
                                AND TABLE.replication=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

query_range_for_experiment_mwresp_r = '''SELECT TABLE.time_mw, TABLE.time_server, TABLE.time_queue, TABLE.time_wb_Queue
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.workload_id=?
                                AND TABLE.replication=?
                                AND TABLE.is_read=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)


query_range_for_experiment_mwresp_w = '''SELECT t.time_mw, t.time_server, t.time_queue, t.time_wb_Queue
                                FROM
                                (
                                SELECT TABLE.time_mw, TABLE.time_server, TABLE.time_queue, TABLE.time_wb_Queue, ROW_NUMBER() OVER (ORDER BY TABLE.round_id) AS rownum
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.workload_id=?
                                AND TABLE.replication=?
                                AND TABLE.is_read=?
                                AND TABLE.is_success=1
                                ) AS t
                                WHERE t.rownum % 10 == 0
                                '''.replace("TABLE", db_table_name_mw)

query_reps_data = '''SELECT TABLE.num_events, TABLE.data
                    FROM TABLE
                    WHERE TABLE.exp_id=?
                    AND TABLE.num_servers=?
                    AND TABLE.machine_id=?
                    AND TABLE.workload_id=?
                    AND TABLE.replication=?
                    AND TABLE.replication=?'''.replace("TABLE", table_name_resp)

conn = sqlite3.connect(db_name)
c = conn.cursor()

use_read = 1
id_map = {1:'read', 0:'write'}

num_servers = [x[0] for x in c.execute(query_num_servers).fetchall()]
replication_factor = ['no', 'all']
replication_factors_num = {}
for server in num_servers:
    replication_factors_num.update({server: {'no': 1, 'all': server}})

ma_id = [x[0] for x in c.execute(query_maid).fetchall()]

results_for_replication = []
results_for_replication_mw = []
for rep_factor in replication_factor:
    result_per_workload=np.zeros((len(num_servers)+1, len(num_servers)*4+1))
    result_per_workload[1:,0] = np.asarray(num_servers)

    result_per_workload_mw = np.zeros((len(num_servers) + 1, len(num_servers)*3 + 1))
    result_per_workload_mw[1:, 0] = np.asarray(num_servers)
    index = 0
    for workload in [1,2,3]:
        server_index = 1
        for num_server in num_servers:

            to_replication_map = replication_factors_num[num_server]
            exp_res = []
            exp_id = [x[0] for x in c.execute(query_expid, (num_server, to_replication_map[rep_factor], workload)).fetchall()]
            print exp_id
            exp_res_mw_resps = np.zeros((len(exp_id), 3))
            row_id=0

            for id in exp_id:
                machine_res = []

                from_id = 1000
                to_id = [x[0] for x in c.execute(query_max_round_ID,
                                                 (id, num_server, workload, to_replication_map[rep_factor])).fetchall()]
                to_id = to_id[0]
                to_id -= from_id
                data_mw_resp_r = c.execute(query_range_for_experiment_mwresp_r,
                                           (id, num_server, from_id, to_id, workload, to_replication_map[rep_factor],
                                            1)).fetchall()
                data_mw_resp_w_temp = c.execute(query_range_for_experiment_mwresp_r,
                                           (id, num_server, from_id, to_id, workload, to_replication_map[rep_factor],
                                            0)).fetchall()


                data_mw_resp_w = data_mw_resp_w_temp
                #ind = 0
                #for item in data_mw_resp_w_temp:
                    #if ind % 10 == 0:
                        #data_mw_resp_w.append(item)
                    #ind += 1
                if use_read == 1:
                    data_mw_resp = data_mw_resp_r
                else:
                    data_mw_resp = data_mw_resp_w
                data_mw_resp = np.asarray(data_mw_resp)
                data_mw_resp_proc = data_mw_resp[:, 0] + data_mw_resp[:, 1]
                exp_res_mw_resps[row_id, 0] = np.median(data_mw_resp_proc, axis=0)
                exp_res_mw_resps[row_id, 1] = np.percentile(data_mw_resp_proc, 90, axis=0)
                exp_res_mw_resps[row_id, 2] = np.percentile(data_mw_resp_proc, 95, axis=0)
                exp_res_mw_resps /= 1000000
                row_id += 1

                for maid in ma_id:
                    data_tem = c.execute(query_range_for_experiment,
                                         (id, num_server, maid, 30, 150, workload, to_replication_map[rep_factor])).fetchall()
                    #data_resp = c.execute(query_reps_data, (id, num_server, maid, workload,to_replication_map[rep_factor])).fetchall()
                    #data_resp = data_resp[0]
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
                machine_res[0] = tp
                exp_res.append(machine_res)
            exp_res = np.average(np.asarray(exp_res), axis=0)
            exp_res[3] = np.sqrt(exp_res[3])
            exp_res_mw_resps = np.average(exp_res_mw_resps, axis=0)
            result_per_workload[server_index, (index*4+1):(index*4+5)] = exp_res
            result_per_workload_mw[server_index, (index*3+1):(index*3+4)] = exp_res_mw_resps
            server_index += 1
        index += 1
    results_for_replication.append([rep_factor, result_per_workload])
    results_for_replication_mw.append([rep_factor, result_per_workload_mw])



plt.rcParams.update(params)
plt.rc('pdf',fonttype = 42)

f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
ax1.set_title("%s replication throughput " % replication_factor[0])
data = results_for_replication[0]
data = data[1]
a = ax1.errorbar(data[:,0], data[:,1] , yerr=data[:, 2],fmt='-o', ecolor='r')
b = ax1.errorbar(data[:,0], data[:,5] , yerr=data[:, 6],fmt='-o', ecolor='r')
c = ax1.errorbar(data[:,0], data[:,9] , yerr=data[:, 10],fmt='-o', ecolor='r')
ax1.grid(color='gray', linestyle='dashed')
ax1.legend([a, b, c], ['1% writes', '5% writes', '10% writes'], loc=2)
ax1.set_ylabel("# operations per second [ops/s]")
ax1.set_xlabel("number of servers")

ax2.set_title("%s replication throughput " % replication_factor[1])
data = results_for_replication[1]
data = data[1]
ax2.errorbar(data[:,0], data[:,1] , yerr=data[:, 2],fmt='-o', ecolor='r')
ax2.errorbar(data[:,0], data[:,5] , yerr=data[:, 6],fmt='-o', ecolor='r')
ax2.errorbar(data[:,0], data[:,9] , yerr=data[:, 10],fmt='-o', ecolor='r')
ax2.grid(color='gray', linestyle='dashed')
ax2.set_xlabel("number of servers")

f.suptitle("Writes experiment: Throughput", fontsize=24, y=1.02)

#plt.legend(lines, names, loc=2)
#plt.title("Max Throughput Experiment: Aggregated throughput", y=1.02)
#plt.ylabel("# operations per second [ops/s]")
#plt.xlabel("number of clients")
#plt.grid(color='gray', linestyle='dashed')

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/writes_exp_tp.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()


#f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
#ax1.set_title("%s replication response time" % replication_factor[0])
#data = results_for_replication[0]
#data = data[1]
#a, = ax1.plot(data[:,0], data[:,3], '-o')
#b, = ax1.plot(data[:,0], data[:,7], '-o')
#c, = ax1.plot(data[:,0], data[:,11], '-o')
#a2, = ax1.plot( data[:, 0], data[:, 4], '-o')

#b2, = ax1.plot(data[:, 0], data[:, 8], '-o')
#c2, = ax1.plot(data[:, 0], data[:, 12], '-o')
#ax1.grid(color='gray', linestyle='dashed')
#ax1.legend([a, b, c], ['1% writes', '5% writes', '10% writes'], loc=2)
#ax1.set_ylabel("time in milliseconds [ms]")
#ax1.set_xlabel("number of servers")

#ax2.set_title("%s replication response time " % replication_factor[1])
#data = results_for_replication[1]
#data = data[1]
#ax2.plot(data[:,0], data[:,3], '-o')
#ax2.plot(data[:,0], data[:,7], '-o')
#ax2.plot(data[:,0], data[:,11], '-o')
#ax2.plot(data[:, 0], data[:, 4], '-o')
#ax2.plot(data[:, 0], data[:, 8], '-o')
#ax2.plot(data[:, 0], data[:, 12], '-o')
#ax2.grid(color='gray', linestyle='dashed')
#ax2.set_xlabel("number of servers")

#plt.legend(lines, names, loc=2)
#plt.title("Max Throughput Experiment: Aggregated throughput", y=1.02)
#plt.ylabel("# operations per second [ops/s]")
#plt.xlabel("number of clients")
#plt.grid(color='gray', linestyle='dashed')

f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
ax1.set_title("%s replication response time" % replication_factor[0])
data = results_for_replication[0]
data = data[1]
a = ax1.errorbar(data[:,0], data[:,3]/1000 , yerr=data[:, 4]/1000,fmt='-o', ecolor='b', capthick=2)
b = ax1.errorbar(data[:,0], data[:,7]/1000 , yerr=data[:, 8]/1000,fmt='-o', ecolor='g', capthick=2)
c = ax1.errorbar(data[:,0], data[:,11]/1000 , yerr=data[:, 12]/1000,fmt='-o', ecolor='r', capthick=2)
ax1.grid(color='gray', linestyle='dashed')
ax1.legend([a, b, c], ['1% writes', '5% writes', '10% writes'], loc=2)
ax1.set_ylabel("time in milliseconds [ms]")
ax1.set_xlabel("number of servers")
ax1.set_xlim([0, 8])

ax2.set_title("%s replication response time " % replication_factor[1])
data = results_for_replication[1]
data = data[1]
ax2.errorbar(data[:,0], data[:,3]/1000 , yerr=data[:, 4]/1000,fmt='-o', ecolor='b', capthick=2)
ax2.errorbar(data[:,0], data[:,7]/1000 , yerr=data[:, 8]/1000,fmt='-o', ecolor='g', capthick=2)
ax2.errorbar(data[:,0], data[:,11]/1000 , yerr=data[:, 12]/1000,fmt='-o', ecolor='r', capthick=2)
ax2.grid(color='gray', linestyle='dashed')
ax2.set_xlabel("number of servers")
ax2.set_xlim([0, 8])

f.suptitle("Writes experiment: Response Time", fontsize=24, y=1.02)

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/writes_exp_resptime.pdf')
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()



f, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
ax1.set_title("%s replication %s mw response time" % (replication_factor[0], id_map[use_read]))
data = results_for_replication_mw[0]
data = data[1]
a, = ax1.plot(data[:,0], data[:,1], '-o')
b, = ax1.plot(data[:,0], data[:,4], '-o')
c, = ax1.plot(data[:,0], data[:,8], '-o')
a2, = ax1.plot(data[:, 0], data[:, 2], '-x')
b2, = ax1.plot(data[:, 0], data[:, 5], '-x')
c2, = ax1.plot(data[:, 0], data[:, 9], '-x')
ax1.grid(color='gray', linestyle='dashed')
ax1.legend([a, b, c, a2, b2, c2], ['median 1% writes', 'median 5% writes', 'median 10% writes', '90th perc 1% writes','90th perc 5% writes', '90th perc 10% writes'], bbox_to_anchor=(0., 1.08, 1., .102), loc=3,
           ncol=2)
ax1.set_ylabel("time in milliseconds [ms]")
ax1.set_xlabel("number of servers")
ax1.set_xlim([0, 8])

ax2.set_title("%s replication %s mw response time " % (replication_factor[0], id_map[use_read]))
data = results_for_replication_mw[1]
data = data[1]
ax2.plot(data[:,0], data[:,1], '-o')
ax2.plot(data[:,0], data[:,4], '-o')
ax2.plot(data[:,0], data[:,8], '-o')
ax2.plot(data[:, 0], data[:, 2], '-x')
ax2.plot(data[:, 0], data[:, 5], '-x')
ax2.plot(data[:, 0], data[:, 9], '-x')
ax2.grid(color='gray', linestyle='dashed')
ax2.set_xlabel("number of servers")
ax2.set_xlim([0, 8])


#plt.legend(lines, names, loc=2)
#plt.title("Max Throughput Experiment: Aggregated throughput", y=1.02)
#plt.ylabel("# operations per second [ops/s]")
#plt.xlabel("number of clients")
#plt.grid(color='gray', linestyle='dashed')

F = plt.gcf()
F.set_size_inches(fig_size)
pdf_pages = PdfPages('../plots/writes_exp_resptime_mw_%s.pdf' % id_map[use_read])
pdf_pages.savefig(F, bbox_inches='tight')
plt.clf()
pdf_pages.close()