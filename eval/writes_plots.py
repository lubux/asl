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

db_name = "writesexp_exp.db"
db_table_name_client = "writesexp_c"
db_table_name_mw = "writesexp_mw"
table_name_resp = "writesexp_resp"

query_num_servers = '''SELECT TABLE.num_servers
                       FROM TABLE
                      GROUP BY TABLE.num_servers
                      ORDER BY TABLE.num_servers'''.replace("TABLE", db_table_name_mw)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 WHERE TABLE.num_servers=? AND TABLE.replication=? AND TABLE.workload_id=?
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name_client)

query_max_round_ID = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.is_read=? '''.replace("TABLE", db_table_name_mw)

query_range_for_experiment = '''SELECT TABLE.time_mw, TABLE.time_server, TABLE.time_queue, TABLE.time_wb_Queue
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.replication=?
                                AND TABLE.workload_id=?
                                AND TABLE.is_read=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

query_max_round_ID_range = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.replication=?
                                AND TABLE.workload_id=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)


if not os.path.isfile("./"+db_name):
    extractor.move_client_data_to_db_writes("../data/writes_moredetailed/", db_name, db_table_name_client, db_table_name_mw, table_name_resp)

conn = sqlite3.connect(db_name)
con = conn.cursor()

for_writes = 1

workload_map = {1:'1 percent', 2:'5 percent', 3:'10 percent'}
num_servers = [x[0] for x in con.execute(query_num_servers).fetchall()]
replication_factor = ['one', 'all']
replication_factors_num = {}
for server in num_servers:
    replication_factors_num.update({server: {'one': 1, 'all': server}})
for workload in [1,2,3]:
    for rep_factor in replication_factor:
        result = []
        for num_server in num_servers:
            cur_dict = replication_factors_num[num_server]
            print num_server
            print cur_dict[rep_factor]
            print workload
            exp_id = [x[0] for x in
                      con.execute(query_expid, (num_server, cur_dict[rep_factor], workload)).fetchall()]
            exp_res = np.zeros((len(exp_id), 5 * 3))
            cur_row=0
            for id in exp_id:
                from_id = 2000
                to_id = [x[0] for x in con.execute(query_max_round_ID_range,
                                                 (id, num_server, cur_dict[rep_factor], workload)).fetchall()]
                #print to_id[0]
                to_id = to_id[0]
                to_id -= from_id

                data_tem = con.execute(query_range_for_experiment, (id, num_server, from_id, to_id, cur_dict[rep_factor], workload, for_writes)).fetchall()
                data = np.asarray(data_tem)
                (X, Y) = data.shape
                data_all = np.zeros((X,Y+1))
                #time_processing = data[:, 0] - data[:, 1] - data[:, 2] - data[:, 3]
                time_processing = data[:, 0] - data[:, 2]
                data_all[:,:-1] = data
                data_all[:, Y] = time_processing

                (X, Y) = data_all.shape
                exp_res[cur_row, 0: 5] = np.median(data_all, axis=0)
                exp_res[cur_row, 5: 10] = np.percentile(data_all, 90, axis=0)
                exp_res[cur_row, 10: 15] = np.percentile(data_all, 95, axis=0)
                cur_row += 1
            exp_res = np.average(exp_res, axis=0)
            exp_res /= 1000000
            result.append(np.append([num_server], exp_res))
        result = np.asarray(result)


        plt.rcParams.update(params)
        plt.rc('pdf',fonttype = 42)

        array_names = ['set', 'get']

        # Four axes, returned as a 2-d array
        x = result[:, 0]
        f, axarr = plt.subplots(2, 2)
        a, = axarr[0, 0].plot(x, result[:, 1], '-o')
        b, = axarr[0, 0].plot(x, result[:, 6], '-o', color='r')
        c, = axarr[0, 0].plot(x, result[:, 11], '-o', color='g')
        axarr[0, 0].grid(color='gray', linestyle='dashed')
        axarr[0, 0].set_title('%s replicas %s mw time' % (rep_factor, array_names[for_writes]))
        axarr[0, 0].set_ylabel("time in milliseconds [ms]")
        axarr[0, 0].legend([a, b, c], ['median time', '90th percentile', '95th percentile'], bbox_to_anchor=(0., 1.08, 1., .102), loc=3, ncol=3)
        axarr[0, 0].set_xlim([2, 8])
        axarr[0, 0].set_ylim(ymin=0)

        axarr[0, 1].plot(x, result[:, 2], '-o')
        axarr[0, 1].plot(x, result[:, 7], '-o', color='r')
        axarr[0, 1].plot(x, result[:, 12], '-o', color='g')
        axarr[0, 1].grid(color='gray', linestyle='dashed')
        axarr[0, 1].set_title('%s replicas %s mc server time' % (rep_factor, array_names[for_writes]))
        axarr[0, 1].set_xlim([2, 8])
        axarr[0, 1].set_ylim(ymin=0)

        axarr[1, 0].plot(x,  result[:, 3], '-o')
        axarr[1, 0].plot(x, result[:, 8], '-o', color='r')
        axarr[1, 0].plot(x, result[:, 13], '-o', color='g')
        axarr[1, 0].grid(color='gray', linestyle='dashed')
        axarr[1, 0].set_title('%s replicas %s queue time' % (rep_factor, array_names[for_writes]))
        axarr[1, 0].set_ylabel("time in milliseconds [ms]")
        axarr[1, 0].set_xlabel("number of servers")
        axarr[1, 0].set_xlim([2, 8])
        axarr[1, 0].set_ylim(ymin=0)

        axarr[1, 1].plot(x, result[:, 5], '-o')
        axarr[1, 1].plot(x, result[:, 10], '-o', color='r')
        axarr[1, 1].plot(x, result[:, 15], '-o', color='g')
        axarr[1, 1].grid(color='gray', linestyle='dashed')
        axarr[1, 1].set_title('%s replicas %s processing time' % (rep_factor, array_names[for_writes]))
        axarr[1, 1].set_xlabel("number of servers")
        axarr[1, 1].set_xlim([2, 8])
        axarr[1, 1].set_ylim(ymin=0)

        f.suptitle("Writes experiment: MW times %s writes" % (workload_map[workload],), fontsize=24, y=1.08)

        # Fine-tune figure; hide x ticks for top plots and y ticks for right plots
        #plt.setp([a.get_xticklabels() for a in axarr[0, :]], visible=False)
        #plt.setp([a.get_yticklabels() for a in axarr[:, 1]], visible=False)
        #f.suptitle("%d threads time in middleware" % num_threads_Id, fontsize=22, y=1.02)

        F = plt.gcf()
        F.set_size_inches(fig_size)
        pdf_pages = PdfPages('../plots/writes_exp_time_mw_percent_write%s_%s_isresd%d.pdf' % (workload_map[workload], rep_factor, for_writes))
        pdf_pages.savefig(F, bbox_inches='tight')
        plt.clf()
        pdf_pages.close()