import memaslap_extractor as extractor
import math
import numpy as np
import os
import re
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from numpy import genfromtxt



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


skip_mw = 50000
mw_data = genfromtxt('../data/longrun/mw.log', delimiter=',')
mw_data = mw_data[skip_mw:(len(mw_data)-skip_mw), 1:] / 1000000


agr_interval = 60
start_id = 300 - agr_interval
end_id = 3900
steps = (end_id-start_id)/agr_interval

conn = sqlite3.connect(db_name)

c = conn.cursor()
ma_id = [x[0] for x in c.execute(query_maid).fetchall()]
res = [[0,0,0,0,0]]

machine_res = []
for maid in ma_id:
    data = np.asarray(c.execute(query_range_for_experiment, (maid, start_id,end_id)).fetchall())
    data[:, 2] = np.square(data[:, 2])
    avg_resp = np.average(data, axis=0)
    machine_res.append([avg_resp[0], avg_resp[1]/1000, avg_resp[2]/1000])
tp = 0
for temp in machine_res:
    tp += temp[0]
machine_res = np.average(np.asarray(machine_res), axis=0)
machine_res[0] = tp
res = np.asarray(machine_res)


tot_time_mw = np.average(mw_data[:,0] + mw_data[:,1])
time_mw = np.average(mw_data[:,0])
server_time = np.average(mw_data[:,1])
queue_time = np.average(mw_data[:,2])
queue_time_tot = np.average(mw_data[:,2]+ mw_data[:,3])
time_mw_without_queue = np.average(mw_data[:,0]-mw_data[:,2])
time_mw_tot_without_queue = np.average(mw_data[:,0]+ mw_data[:,1]-mw_data[:,2])

print "Cl tp: %.0f" % (res[0],)
print "Cl resp: %.2f" % (res[1],)

print "MW tot: %.2f" % (tot_time_mw,)
print "MW only: %.2f" % (time_mw,)
print "Server time: %.2f" % (server_time,)
print "Queue time: %.2f" % (queue_time,)
print "Queue time tot (wb): %.2f" % (queue_time_tot,)
print "MW only without queue: %.2f" % (time_mw_without_queue,)
print "MW tot without queue: %.2f" % (time_mw_tot_without_queue,)

print "Tot without queue: %.2f" % (res[1]-queue_time,)
print "C->MW net time: %.2f" % (res[1]-tot_time_mw,)