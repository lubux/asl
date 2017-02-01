import memaslap_extractor as extractor
import math
import numpy as np
import os
import re
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


# A: workload -1 large 1 small
# B: Replication -1 all 1: no
# 1 1 -1 -1  1
# 2 1  1 -1 -1
# 3 1 -1  1 -1
# 4 1  1  1  1


db_name = "2k_exp.db"
db_table_name_client = "kexp_c"
db_table_name_mw = "kexp_mw"
table_name_resp = "kexp_resp"


query_maid = '''SELECT TABLE.machine_id
                FROM TABLE
                GROUP BY TABLE.machine_id
                ORDER BY TABLE.machine_id'''.replace("TABLE", db_table_name_client)


query_range_for_experiment_tp = '''SELECT TABLE.tps, TABLE.avg, TABLE.std
                                FROM TABLE
                                WHERE TABLE.exp_id=?
                                AND TABLE.machine_id=?
                                AND TABLE.num_servers=?
                                AND TABLE.round_id>?
                                AND TABLE.round_id<=?
                                AND TABLE.replication=? AND NOT TABLE.std is null'''.replace("TABLE", db_table_name_client)


if not os.path.isfile("./"+db_name):
    extractor.move_client_data_to_db_rep("../data/2kexp/", db_name, db_table_name_client, db_table_name_mw, table_name_resp)

conn = sqlite3.connect(db_name)
conn = conn.cursor()

num_Server = 3

names_vals = ['I', 'A', 'B', 'AB']

mat_int = np.asarray([[1,-1,-1,1], [1,1,-1,-1], [1,-1,1,-1], [1,1,1,1]])

r_param = 5
t_values = {3:1.86, 4:1.78, 5:1.746}
exp_ids = range(1, r_param+1)

experiments_configs =[[2, num_Server], [1, num_Server], [2, 1], [1, 1]]
configuration_iter=0

tp_y = np.zeros((4, r_param))
resp_y = np.zeros((4, r_param))

ma_id = [x[0] for x in conn.execute(query_maid).fetchall()]

for config in experiments_configs:
    for exp_id in exp_ids:
        resp_machines = []
        tp_machines = []
        is_first_1 = True
        for id in ma_id:
            data_tp = conn.execute(query_range_for_experiment_tp,
                                   (exp_id, id, config[0], 30, 150, config[1])).fetchall()
            data_tp = np.asarray(data_tp)

            #if is_first_1:
             #   sum_tp = data_tp[:, 0]
              #  is_first_1 = False
            #else:
             #   sum_tp += data_tp[:, 0]

            data_tp[:, 2] = np.square(data_tp[:, 2])
            avg = np.average(data_tp, axis=0)
            std = np.std(data_tp, axis=0)
            resp_machines.append(avg[1])
            tp_machines.append(avg[0])
        tp = 0
        for temp in tp_machines:
            tp += temp
        resp_exp = np.average(np.asarray(resp_machines))
        tp_exp = tp
        tp_y[configuration_iter, exp_id-1] = tp_exp
        resp_y[configuration_iter, exp_id - 1] = resp_exp
    configuration_iter += 1
resp_y = resp_y/1000

tp_y_avg = np.average(tp_y, axis=1)
resp_y_avg = np.average(resp_y, axis=1)
bsp_book = np.asarray([[15,18,12], [45, 48, 51], [25, 28, 19], [75, 75, 81]])
bsp_book2 = np.asarray([[85.10, 79.50, 147.90], [0.891, 1.047, 1.072], [0.955, 0.933, 1.122], [0.0148, 0.0126, 0.0118]])

def compute_q_params(y_data, mat_int):
    res = np.transpose(mat_int).dot(y_data)
    res = res / 4
    return res


def compute_SS_err_params(q_data):
    return 4 * r_param * np.square(q_data)


def compute_SSY(mat_ys):
    return np.sum(np.square(mat_ys))


def compute_SSE(ssy_err, q_data):
    return ssy_err - (4 * r_param * np.sum(np.square(q_data)))


def compute_SST(ssy, ss0):
    return ssy - ss0


def compute_explanations(vars, sst, sse):
    temp = vars / sst
    temp = temp.tolist()
    temp.append(sse/sst)
    return np.asarray(temp)


def compute_conf_interval(qs, t_val, sse):
    (x,) = qs.shape
    res = np.zeros((x, 2))
    s_e = np.sqrt(sse/(4*(r_param-1)))
    s_q = s_e / np.sqrt(4*r_param)
    diff = s_q * t_val
    res[:,0] = qs - diff
    res[:,1] = qs + diff
    return res

def gen_table_start(data_y_tp, data_y_resp):
    y_avg = np.average(data_y_tp, axis=1)
    y_resp_avg = np.average(data_y_resp, axis=1)
    print "TABLE"
    ones = mat_int.tolist()
    for row in range(len(ones)):
        cur_row = ones[row]
        print "\hline " +\
              ' & '.join([str(x) for x in cur_row]) + \
              ' & (' + ','.join(["%.2f" % x for x in data_y_tp[row]]) + ') & ' + "%.2f" % y_avg[row] \
              + ' & (' + ','.join(["%.0f" % x for x in data_y_resp[row]]) + ') & ' + "%.0f" % y_resp_avg[row] + " \\\\"


err_table = ["SSY", "SS0", "SSA", "SSB", "SSAB", "SSE", "SST"]

def gen_table_results(data_y, mat_int):
    y_avg = np.average(data_y, axis=1)
    q_params = compute_q_params(y_avg, mat_int)
    qerr_params = compute_SS_err_params(q_params)
    ssy = compute_SSY(data_y)
    sse = compute_SSE(ssy, q_params)
    sst = compute_SST(ssy, qerr_params[0])
    effect = compute_explanations(qerr_params, sst, sse) * 100
    intervals = compute_conf_interval(q_params, t_values[r_param], sse)
    intervals = intervals.tolist()
    print "TABLE"
    for row in range(len(y_avg)):
        cur_interval = intervals[row]
        if row == 0:
            print "\hline " + names_vals[row] + " & " + "%.2f" % q_params[row] + " & " + " & (" + ",".join(["%.2f" % float(x) for x in cur_interval]) + ")" + " \\\\"
        else:
            print "\hline "+ names_vals[row] + " & " + "%.2f" % q_params[row] + " & " + "%.2f" % effect[row] + ' & (' + ','.join(["%.2f" % float(x) for x in cur_interval]) + ")" + " \\\\"

    print "\hline e &  & " + "%.2f" % effect[len(y_avg)] + " & \\\\"

    print "ERR TABLE"
    print "\hline "+ err_table[0] + " & %.2f" % ssy + " \\\\"
    for ind in range(len(qerr_params.tolist())):
        print "\hline " + err_table[ind+1] + " & %.2f" % qerr_params[ind]+ " \\\\"
    print "\hline "+ err_table[5] + " & %.2f" % sse + " \\\\"
    print "\hline " + err_table[6] + " & %.2f" % sst + " \\\\"



gen_table_start(resp_y, tp_y)
gen_table_results(resp_y, mat_int)
gen_table_results(tp_y, mat_int)
#tab_str = "\hline Number of servers & 3, 5, 7 \\ "