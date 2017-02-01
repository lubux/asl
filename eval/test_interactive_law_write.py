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
db_table_name_client_seperate = "writesexp_c_sep"
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

query_range_for_experiment_seperate = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.machine_id=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.workload_id=?
                                AND TABLE.is_get=?
                                AND TABLE.replication=? AND NOT TABLE.std is null'''.replace("TABLE", db_table_name_client_seperate)

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

extractor.move_client_data_to_db_writes_seperat("../data/writesexp/", db_name, db_table_name_client_seperate)
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
results_for_replication_pred_resp = []
results_for_replication_get = []
results_for_replication_set = []


results_for_replication_mw = []
for rep_factor in replication_factor:
    result_per_workload=np.zeros((len(num_servers)+1, len(num_servers)*4+1))
    result_per_workload_get = np.zeros((len(num_servers) + 1, len(num_servers) * 4 + 1))
    result_per_workload_set = np.zeros((len(num_servers) + 1, len(num_servers) * 4 + 1))
    result_pred_pre_workload = []

    result_per_workload[1:,0] = np.asarray(num_servers)
    result_per_workload_get[1:, 0] = np.asarray(num_servers)
    result_per_workload_set[1:, 0] = np.asarray(num_servers)

    result_per_workload_mw = np.zeros((len(num_servers) + 1, len(num_servers)*3 + 1))
    result_per_workload_mw[1:, 0] = np.asarray(num_servers)
    index = 0
    for workload in [1,2,3]:
        server_index = 1

        resp_server_res = []
        for num_server in num_servers:

            to_replication_map = replication_factors_num[num_server]
            exp_res = []
            exp_res_resp = []
            exp_res_set = []
            exp_res_get = []
            exp_id = [x[0] for x in c.execute(query_expid, (num_server, to_replication_map[rep_factor], workload)).fetchall()]
            print exp_id
            exp_res_mw_resps = np.zeros((len(exp_id), 3))
            row_id=0

            for id in exp_id:
                machine_res = []
                machine_res_get = []
                machine_res_set = []

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


                is_first_1 = True
                list_resp = []
                for maid in ma_id:
                    data_tem = c.execute(query_range_for_experiment,
                                         (id, num_server, maid, 30, 150, workload, to_replication_map[rep_factor])).fetchall()

                    data_tem_set = c.execute(query_range_for_experiment_seperate,
                                         (id, num_server, maid, 30, 150, workload, 0,
                                          to_replication_map[rep_factor])).fetchall()

                    data_tem_get = c.execute(query_range_for_experiment_seperate,
                                         (id, num_server, maid, 30, 150, workload, 1,
                                          to_replication_map[rep_factor])).fetchall()
                    #data_resp = c.execute(query_reps_data, (id, num_server, maid, workload,to_replication_map[rep_factor])).fetchall()
                    #data_resp = data_resp[0]
                    if len(data_tem) == 0:
                        print "no data!!"
                        continue
                    data = np.asarray(data_tem)
                    data_set = np.asarray(data_tem_set)
                    data_get = np.asarray(data_tem_get)
                    #print data.shape
                    #data_resp = data[:, 1]
                    #list_resp += data_resp

                    if is_first_1:
                        sum_tp = data[:, 0]
                        is_first_1 = False
                    else:
                        sum_tp += data[:, 0]

                    data[:, 2] = np.square(data[:, 2])
                    avg = np.average(data, axis=0)
                    std = np.std(data, axis=0)
                    machine_res.append([avg[0], std[0], avg[1], avg[2]])

                    data_set[:, 2] = np.square(data_set[:, 2])
                    avg = np.average(data_set, axis=0)
                    std = np.std(data_set, axis=0)
                    machine_res_set.append([avg[0], std[0], avg[1], avg[2]])

                    data_get[:, 2] = np.square(data_get[:, 2])
                    avg = np.average(data_get, axis=0)
                    std = np.std(data_get, axis=0)
                    machine_res_get.append([avg[0], std[0], avg[1], avg[2]])

                #avg_resp_local = reduce(lambda x, y: x + y, list_resp) / 3
                print sum_tp
                pred_resp = 192/sum_tp
                avg_pred_resp = np.average(pred_resp)
                exp_res_resp.append(avg_pred_resp)

                tp = 0
                tp_compare = np.average(sum_tp, axis=0)
                for temp in machine_res:
                    tp += temp[0]
                print "Should %s Is %s" %(str(tp_compare), str(tp))
                machine_res = np.average(np.asarray(machine_res), axis=0)
                machine_res[0] = tp
                machine_res[0] = tp
                exp_res.append(machine_res)

                tp = 0
                for temp in machine_res_get:
                    tp += temp[0]
                machine_res_get = np.average(np.asarray(machine_res_get), axis=0)
                machine_res_get[0] = tp
                exp_res_get.append(machine_res_get)

                tp = 0
                for temp in machine_res_set:
                    tp += temp[0]
                machine_res_set = np.average(np.asarray(machine_res_set), axis=0)
                machine_res_set[0] = tp
                exp_res_set.append(machine_res_set)

            exp_res = np.average(np.asarray(exp_res), axis=0)
            exp_res_resp = np.average(np.asarray(exp_res_resp), axis=0)
            resp_server_res.append(exp_res_resp)

            exp_res[3] = np.sqrt(exp_res[3])
            exp_res_mw_resps = np.average(exp_res_mw_resps, axis=0)
            result_per_workload[server_index, (index*4+1):(index*4+5)] = exp_res
            result_per_workload_mw[server_index, (index*3+1):(index*3+4)] = exp_res_mw_resps

            exp_res_get = np.average(np.asarray(exp_res_get), axis=0)
            exp_res_get[3] = np.sqrt(exp_res_get[3])
            result_per_workload_get[server_index, (index * 4 + 1):(index * 4 + 5)] = exp_res_get

            exp_res_set = np.average(np.asarray(exp_res_set), axis=0)
            exp_res_set[3] = np.sqrt(exp_res_set[3])
            result_per_workload_set[server_index, (index * 4 + 1):(index * 4 + 5)] = exp_res_set

            server_index += 1
        index += 1
        result_pred_pre_workload.append(resp_server_res)
    results_for_replication_pred_resp.append([rep_factor, np.asarray(result_pred_pre_workload) * 1000])
    results_for_replication.append([rep_factor, result_per_workload])
    results_for_replication_get.append([rep_factor, result_per_workload_get])
    results_for_replication_set.append([rep_factor, result_per_workload_set])
    results_for_replication_mw.append([rep_factor, result_per_workload_mw])


num_users = 64 * 3

data = results_for_replication[0]
data = data[1]



print "one"

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time

print "all"

data = results_for_replication[1]
data = data[1]
# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time


print "GET"

data = results_for_replication_get[0]
data = data[1]

print "one"

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time

print "all"

data = results_for_replication_get[1]
data = data[1]
# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time


print "SET"

data = results_for_replication_set[0]
data = data[1]

print "one"

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time

print "all"

data = results_for_replication_set[1]
data = data[1]
# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = (num_users / data[1:,1]) * 1000
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = (num_users / data[1:,5]) * 1000
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = (num_users / data[1:,9]) * 1000
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time


print "SECOND_GRANULARITY"

data_resp = results_for_replication_pred_resp[0]
data_resp = data_resp[1]

data = results_for_replication[0]
data = data[1]

print "one"

# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = data_resp[0,:]
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time = data_resp[1,:]
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time = data_resp[2,:]
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time

print "all"

data_resp = results_for_replication_pred_resp[1]
data_resp = data_resp[1]


data = results_for_replication_get[1]
data = data[1]
# R=N/X - Z N:Users , X X:tp Z:thinktime
pred_time = data_resp[0,:]
print pred_time
diff_time = pred_time - (data[1:,3]/1000)
print data[1:,3]/1000
print diff_time

pred_time =  data_resp[1,:]
print pred_time
diff_time = pred_time - (data[1:,7]/1000)
print data[1:,7]/1000
print diff_time

pred_time =  data_resp[2,:]
print pred_time
diff_time = pred_time - (data[1:,11]/1000)
print data[1:,11]/1000
print diff_time










