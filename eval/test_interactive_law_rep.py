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

db_name = "replication_exp.db"
db_table_name_client = "repexp_c"
db_table_name_mw = "repexp_mw"
table_name_resp = "repexp_resp"

query_num_servers = '''SELECT TABLE.num_servers
                       FROM TABLE
                      GROUP BY TABLE.num_servers
                      ORDER BY TABLE.num_servers'''.replace("TABLE", db_table_name_mw)

query_expid = '''SELECT TABLE.exp_id
                 FROM TABLE
                 WHERE TABLE.num_servers=? AND TABLE.replication=?
                 GROUP BY TABLE.exp_id
                 ORDER BY TABLE.exp_id'''.replace("TABLE", db_table_name_mw)

query_max_round_ID = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.is_read=? '''.replace("TABLE", db_table_name_mw)

query_max_round_ID_range = '''SELECT MAX(TABLE.round_id)
                        FROM TABLE WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.replication=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name_client)

query_range_for_experiment = '''SELECT TABLE.time_mw, TABLE.time_server, TABLE.time_queue, TABLE.time_wb_Queue
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.replication=?
                                AND TABLE.is_read=?
                                AND TABLE.is_success=1'''.replace("TABLE", db_table_name_mw)

query_range_for_experiment_tp = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.machine_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.replication=? AND NOT TABLE.std is null'''.replace("TABLE", db_table_name_client)



if not os.path.isfile("./"+db_name):
    extractor.move_client_data_to_db_rep("../data/repexp/", db_name, db_table_name_client, db_table_name_mw, table_name_resp)

conn = sqlite3.connect(db_name)
conn = conn.cursor()


for_writes = 1
num_servers = [x[0] for x in conn.execute(query_num_servers).fetchall()]
replication_factor = ['one', 'half', 'all']
tp_res_dict = {}
resp_res_dict = {}
replication_factors_num = {}
for server in num_servers:
    replication_factors_num.update({server: {'one': 1, 'half': (server/2+1), 'all': server}})

ma_id = [x[0] for x in conn.execute(query_maid).fetchall()]

for rep_factor in replication_factor:
    max_round = [x[0] for x in conn.execute(query_max_round_ID, (for_writes,)).fetchall()]
    max_round = max_round[0]
    interval = 20
    min_round = 1 + interval
    max_round -= interval
    result = []
    result_tp = []
    result_resp = []
    for num_server in num_servers:
        cur_dict = replication_factors_num[num_server]
        exp_id = [x[0] for x in conn.execute(query_expid, (num_server, cur_dict[rep_factor])).fetchall()]
        exp_res = np.zeros((len(exp_id), 5 * 3))
        exp_res_tp = np.zeros((len(exp_id), 4))
        exp_res_resp = []
        cur_row=0
        for id in exp_id:
            from_id = 2000
            to_id = [x[0] for x in conn.execute(query_max_round_ID_range,
                                             (id, num_server, cur_dict[rep_factor])).fetchall()]
            print to_id[0]
            to_id = to_id[0]
            to_id -= from_id

            print cur_dict[rep_factor]
            data_tem = conn.execute(query_range_for_experiment, (id, num_server, min_round, max_round, cur_dict[rep_factor], 1)).fetchall()
            data_writes = conn.execute(query_range_for_experiment,(id, num_server, min_round, max_round, cur_dict[rep_factor], 0)).fetchall()
            data_writes_sampled = []
            count = 0
            for line in data_writes:
                if count % 10 == 0:
                    data_writes_sampled.append(line)
                count += 1
            data = np.asarray(data_tem+data_writes_sampled)
            (X, Y) = data.shape
            data_all = np.zeros((X,Y+1))
            #time_processing = data[:, 0] - data[:, 1] - data[:, 2] - data[:, 3]
            time_processing = data[:, 0] - data[:, 2]
            data_all[:,:-1] = data
            data_all[:, Y] = time_processing

            (X, Y) = data_all.shape
            exp_res[cur_row, 0: 5] = np.average(data_all, axis=0)
            exp_res[cur_row, 5: 10] = np.percentile(data_all, 90, axis=0)
            exp_res[cur_row, 10: 15] = np.percentile(data_all, 95, axis=0)

            machine_res = []

            is_first_1 = True
            for maid in ma_id:
                data_tp = conn.execute(query_range_for_experiment_tp,
                                    (id, maid, num_server, 30, 150, cur_dict[rep_factor])).fetchall()
                data_tp = np.asarray(data_tp)

                if is_first_1:
                    sum_tp = data_tp[:, 0]
                    is_first_1 = False
                else:
                    sum_tp += data_tp[:, 0]

                data_tp[:, 2] = np.square(data_tp[:, 2])
                avg = np.average(data_tp, axis=0)
                std = np.std(data_tp, axis=0)
                machine_res.append([avg[0], std[0], avg[1], avg[2]])
                if maid==2 and id==1 and cur_dict[rep_factor] == 4 and num_server==7:
                    plt.rcParams.update(params)
                    plt.rc('pdf', fonttype=42)
                    f, (ax1, ax2) = plt.subplots(1, 2)
                    ax1.errorbar(np.arange(len(data_tp)), data_tp[:,1] / 1000, yerr=np.sqrt(data_tp[:, 2])/1000,fmt='-o', ecolor='r')
                    ax1.set_ylabel("response time [ms]")
                    ax2.plot(np.arange(len(data_tp)), data_tp[:, 0], '-o')
                    ax2.set_ylabel("operations per second [ops/s]")
                    F = plt.gcf()
                    F.set_size_inches(fig_size)
                    pdf_pages = PdfPages('./int_law.pdf')
                    pdf_pages.savefig(F, bbox_inches='tight')
                    plt.clf()
                    pdf_pages.close()


            pred_resp = 192 / sum_tp
            avg_pred_resp = np.average(pred_resp)

            tp = 0
            for temp in machine_res:
                tp += temp[0]
            machine_res = np.average(np.asarray(machine_res), axis=0)
            exp_res_tp[cur_row, :] = np.asarray([tp, machine_res[1], machine_res[2], machine_res[3]])
            exp_res_resp.append(avg_pred_resp)

            cur_row += 1
        exp_res = np.average(exp_res, axis=0)
        exp_res_tp = np.average(exp_res_tp, axis=0)
        exp_res_tp[3] = np.sqrt(exp_res_tp[3])
        exp_res /= 1000000

        exp_res_resp = np.average(np.asarray(exp_res_resp), axis=0)

        result.append(np.append([num_server], exp_res))
        result_tp.append(np.append([num_server], exp_res_tp))
        result_resp.append(np.append([num_server], exp_res_resp * 1000))
    result = np.asarray(result)
    result_tp = np.asarray(result_tp)
    result_resp = np.asarray(result_resp)

    tp_res_dict[rep_factor] = result_tp
    resp_res_dict[rep_factor] = result_resp


rep_factros = ["no rep", "rep half", "rep all"]

print "ALL GRANULARITY"
num_users = 64 * 3
rep_factor = 'one'
result_tp = tp_res_dict[rep_factor]

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / (result_tp[:, 1]))* 1000
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[0], result_tp[ind, 0])
    print "\hline " + string_name + " & " + "%.0f" % result_tp[ind, 1] + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"


# R=N/X - Z N:Users , X X:tp Z:thinktime
rep_factor = 'half'
result_tp = tp_res_dict[rep_factor]
pred_time = (num_users / (result_tp[:, 1]))* 1000
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[1], result_tp[ind, 0])
    print "\hline " + string_name + " & " + "%.0f" % result_tp[ind, 1] + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"

# R=N/X - Z N:Users , X X:tp Z:thinktime
rep_factor = 'all'
result_tp = tp_res_dict[rep_factor]
pred_time = (num_users / (result_tp[:, 1])) * 1000
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[2], result_tp[ind, 0])
    print "\hline " + string_name + " & " + "%.0f" % result_tp[ind, 1] + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"


print "SECOND GRANULARITY"
print "one"
rep_factor = 'one'
result_tp = tp_res_dict[rep_factor]
result_tp_resp = resp_res_dict[rep_factor]

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = result_tp_resp[:,1]
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[0], result_tp[ind, 0])
    print "\hline " + string_name + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"


# R=N/X - Z N:Users , X X:tp Z:thinktime
rep_factor = 'half'
result_tp = tp_res_dict[rep_factor]
result_tp_resp = resp_res_dict[rep_factor]
#print "half"
pred_time = result_tp_resp[:,1]
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[1], result_tp[ind, 0])
    print "\hline " + string_name + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"

# R=N/X - Z N:Users , X X:tp Z:thinktime
rep_factor = 'all'
result_tp = tp_res_dict[rep_factor]
result_tp_resp = resp_res_dict[rep_factor]

#print "all"
pred_time = result_tp_resp[:,1]
#print pred_time
diff_time = pred_time - (result_tp[:, 3]/1000)
#print result_tp[:, 3]/1000
#print result_tp[:, 4]/1000
#print diff_time

tmp = result_tp[:, 3]/1000
for ind in range(len(diff_time)):
    string_name = "%s, %d servers" % (rep_factros[2], result_tp[ind, 0])
    print "\hline " + string_name + " & %.2f" % tmp[ind] + " & %.2f" % pred_time[ind] + " & %.2f" % diff_time[ind] + " \\\\"