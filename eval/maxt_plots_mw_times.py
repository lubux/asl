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

db_name = "maxtpexp.db"
db_table_name_client = "maxtpexp_c"
db_table_name_mw = "maxtpexp_mw"


query_num_servers = '''SELECT TABLE.num_servers
                       FROM TABLE
                       GROUP BY TABLE.num_clients
                       ORDER BY TABLE.num_clients'''.replace("TABLE", db_table_name_mw)

query_clients = '''SELECT TABLE.num_clients
                   FROM TABLE
                   GROUP BY TABLE.num_clients
                   ORDER BY TABLE.num_clients'''.replace("TABLE", db_table_name_client)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 WHERE TABLE.num_threads=? AND TABLE.num_clients=?
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name_mw)

query_max_round_ID = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE'''.replace("TABLE", db_table_name_mw)

query_max_round_ID_range = '''SELECT MIN(TABLE.round_id), MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.exp_id=?
                                AND TABLE.num_clients=?
                                AND TABLE.num_threads=?
                                AND TABLE.is_read=1
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

query_range_for_experiment = '''SELECT TABLE.time_mw, TABLE.time_server, TABLE.time_queue, TABLE.time_wb_Queue
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_clients=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.num_threads=?
                                AND TABLE.is_read=1
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

conn = sqlite3.connect(db_name)
curs = conn.cursor()

num_threads_Ids = [16, 32, 48, 64]
for num_threads_Id in num_threads_Ids:
    result = []
    for num_client_tuple in curs.execute(query_clients).fetchall():
        num_client = num_client_tuple[0]
        exp_id = [x[0] for x in curs.execute(query_expid, (num_threads_Id, num_client)).fetchall()]
        if len(exp_id) < 1:
            np.append([num_client * 5], np.asarray([0 for x in range(15)]))
            continue
        exp_res = np.zeros((len(exp_id), 5 * 3))
        cur_row=0
        for id in exp_id:
            skip_time = 2000
            range_temp = curs.execute(query_max_round_ID_range,
                                          (id, num_client, num_threads_Id)).fetchall()
            range_temp = range_temp[0]
            print range_temp
            from_id = range_temp[0] + skip_time
            to_id = range_temp[1] - skip_time

            data_tem = curs.execute(query_range_for_experiment, (id, num_client, from_id, to_id, num_threads_Id)).fetchall()
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
        result.append(np.append([num_client*5], exp_res))
    result = np.asarray(result)


    plt.rcParams.update(params)
    plt.rc('pdf',fonttype = 42)

    # Four axes, returned as a 2-d array
    x = result[:, 0]
    f, axarr = plt.subplots(2, 2)
    a, = axarr[0, 0].plot(x, result[:, 1], '-o')
    b, = axarr[0, 0].plot(x, result[:, 6], '-o', color='r')
    c, = axarr[0, 0].plot(x, result[:, 11], '-o', color='g')
    axarr[0, 0].grid(color='gray', linestyle='dashed')
    axarr[0, 0].set_title('%d-threads mw time' % num_threads_Id)
    axarr[0, 0].set_ylabel("time in milliseconds [ms]")
    axarr[0, 0].legend([a, b, c], ['median time', '90th percentile', '95th percentile'], bbox_to_anchor=(0., 1.08, 1., .102), loc=3, ncol=3)

    axarr[0, 1].plot(x, result[:, 2], '-o')
    axarr[0, 1].plot(x, result[:, 7], '-o', color='r')
    axarr[0, 1].plot(x, result[:, 12], '-o', color='g')
    axarr[0, 1].grid(color='gray', linestyle='dashed')
    axarr[0, 1].set_title('%d-threads mc server time' % num_threads_Id)

    axarr[1, 0].plot(x,  result[:, 3], '-o')
    axarr[1, 0].plot(x, result[:, 8], '-o', color='r')
    axarr[1, 0].plot(x, result[:, 13], '-o', color='g')
    axarr[1, 0].grid(color='gray', linestyle='dashed')
    axarr[1, 0].set_title('%d-threads queue time' % num_threads_Id)
    axarr[1, 0].set_ylabel("time in milliseconds [ms]")
    axarr[1, 0].set_xlabel("number of clients")

    axarr[1, 1].plot(x, result[:, 5], '-o')
    axarr[1, 1].plot(x, result[:, 10], '-o', color='r')
    axarr[1, 1].plot(x, result[:, 15], '-o', color='g')
    axarr[1, 1].grid(color='gray', linestyle='dashed')
    axarr[1, 1].set_title('%d-threads processing time' % num_threads_Id)
    axarr[1, 1].set_xlabel("number of clients")

    # Fine-tune figure; hide x ticks for top plots and y ticks for right plots
    plt.setp([a.get_xticklabels() for a in axarr[0, :]], visible=False)
    #plt.setp([a.get_yticklabels() for a in axarr[:, 1]], visible=False)
    #f.suptitle("%d threads time in middleware" % num_threads_Id, fontsize=22, y=1.02)
    #plt.sca(axarr[0, 0])
    #plt.yticks(np.arange(0, 15, 2))
    #plt.sca(axarr[0, 1])
    #plt.yticks(np.arange(0, 15, 2))
    #plt.sca(axarr[1, 0])
    #plt.yticks(np.arange(0, 11, 1))
    #plt.sca(axarr[1, 1])
    #plt.yticks(np.arange(0, 11, 1))

    F = plt.gcf()
    F.set_size_inches(fig_size)
    pdf_pages = PdfPages('../plots/maxtp_throughput_resp'+str(num_threads_Id)+'.pdf')
    pdf_pages.savefig(F, bbox_inches='tight')
    plt.clf()
    pdf_pages.close()