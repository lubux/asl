import numpy as np
import os
import re
import sqlite3

TOTAL_STAT = "Total Statistics"
GET_STAT = "Get Statistics"
SET_STAT = "Set Statistics"
PER_STAT = "Period"


def extract_data(file_path):
    file = open(file_path, 'r')
    in_total_stat = False
    res = []
    for line in file:
        if TOTAL_STAT in line:
            in_total_stat = True
            continue
        if in_total_stat:
            if PER_STAT in line:
                cells = line.split()
                cells.pop(0)
                res.append(cells)
                in_total_stat = False
    temp = np.asarray(res)
    file.close()
    return temp.astype(float)

def extract_data_set(file_path):
    file = open(file_path, 'r')
    in_total_stat = False
    res = []
    for line in file:
        if SET_STAT in line:
            in_total_stat = True
            continue
        if in_total_stat:
            if PER_STAT in line:
                cells = line.split()
                cells.pop(0)
                res.append(cells)
                in_total_stat = False
    temp = np.asarray(res)
    file.close()
    return temp.astype(float)

def extract_data_get(file_path):
    file = open(file_path, 'r')
    in_total_stat = False
    res = []
    for line in file:
        if GET_STAT in line:
            in_total_stat = True
            continue
        if in_total_stat:
            if PER_STAT in line:
                cells = line.split()
                cells.pop(0)
                res.append(cells)
                in_total_stat = False
    temp = np.asarray(res)
    file.close()
    return temp.astype(float)


FINAL_GET = re.compile('Get Statistics \\((\d+) events\\)')
FINAL_SET = re.compile('Set Statistics \\((\d+) events\\)')
FINAL_TOTAL = re.compile('Total Statistics \\((\d+) events\\)')
FINAL_LOG2 = 'Log2 Dist'

def extract_data_median_resp(file_path):
    file = open(file_path, 'r')
    in_total_stat = False
    in_log2_parse = False
    in_log2_count = 0
    res = []
    temp = []
    log_2_data = []
    for line in file:
        if FINAL_LOG2 in line and in_total_stat:
            in_log2_parse = True
            continue
        if in_log2_parse:
            splits = line.split()
            if len(splits)>1:
                del splits[0]
                log_2_data += [int(x) for x in splits]
            in_log2_count += 1
            if in_log2_count == 4:
                if len(log_2_data)<16:
                    log_2_data += [0 for x in range(16-len(log_2_data))]
                temp += log_2_data
                res.append(temp)
                in_total_stat = False
                in_log2_parse = False
                in_log2_count = 0
                log_2_data = []
            continue

        match = FINAL_GET.match(line)
        if match:
            temp = [1, int(match.group(1))]
            in_total_stat = True
            continue
        match = FINAL_SET.match(line)
        if match:
            temp = [2, int(match.group(1))]
            in_total_stat = True
            continue
        match = FINAL_TOTAL.match(line)
        if match:
            temp = [3, int(match.group(1))]
            in_total_stat = True
            continue

            continue
    return np.asarray(res)

p = re.compile('clientlog_(\d+)-(\d+)-(\d+)-(\d+).txt')
p_mw = re.compile('mw_(\d+)-(\d+)-(\d+)')


def extract_resp_tp_from_directory(directory):
    temp_res = []
    for filename in os.listdir(directory):
        match = p.match(filename)
        if match:
            machine_id = match.group(2)
            num_clients = match.group(1)
            data = extract_data(filename)
            if len(data)>0:
                (x,y) = data.shape
                avg_data = np.average(data[1:x-2, :], axis=0)
                temp_res.append([float(machine_id), float(num_clients)] + avg_data.tolist())


def move_client_data_to_db(directory, db_name, table_name_client, table_name_mw, table_names=('round_id','num_clients',)):
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_client)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, round_id INTEGER, machine_id INTEGER, num_clients INTEGER,  num_threads INTEGER,
        time INTEGER, ops INTEGER, tps INTEGER, net REAL, miss INTEGER, min INTEGER, max INTEGER, avg INTEGER,
         std REAL, geo REAL)''' % table_name_client)
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_mw)
    conn.cursor().execute('''CREATE TABLE %s(round_id INTEGER, time STRING, num_clients INTEGER, exp_id INTEGER,  num_threads INTEGER, time_mw INTEGER,
            time_server INTEGER, time_queue INTEGER,
            time_wb_Queue INTEGER, is_read INTEGER, is_success INTEGER)''' % table_name_mw)
    conn.commit()
    for filename in os.listdir(directory):
        match = p.match(filename)
        if match:
            machine_id = match.group(2)
            num_clients = match.group(1)
            exp_id = match.group(3)
            num_t = match.group(4)
            data = extract_data(directory+filename)
            round = 1
            res = []
            for row in data.tolist():
                row.insert(0, float(num_t))
                row.insert(0, float(num_clients))
                row.insert(0, float(machine_id))
                row.insert(0, float(round))
                row.insert(0, float(exp_id))
                round += 1
                temp = tuple([int(x) if x.is_integer() else float(x) for x in row])
                res.append(temp)
            c = conn.cursor()
            c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_client, res)
            conn.commit()
        match = p_mw.match(filename)
        if match:
            num_clients = match.group(1)
            exp_id = match.group(2)
            num_t = match.group(3)
            file = open(directory+filename, 'r')
            res = []
            round=1
            for line in file:
                splits = line.split(",")
                temp = (round, splits[0], num_clients, exp_id, num_t, int(splits[1]), int(splits[2]),
                         int(splits[3]), int(splits[4]), int(splits[5]),int(splits[6]))
                res.append(temp)
                round += 1
            file.close()
            c = conn.cursor()
            c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?)' % table_name_mw, res)
            conn.commit()
    conn.close()


def move_client_data_to_db_rep(directory, db_name, table_name_client, table_name_mw, table_name_resp):
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_client)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, round_id INTEGER, machine_id INTEGER, num_servers INTEGER,  replication INTEGER,
        time INTEGER, ops INTEGER, tps INTEGER, net REAL, miss INTEGER, min INTEGER, max INTEGER, avg INTEGER,
         std REAL, geo REAL)''' % table_name_client)
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_mw)
    conn.cursor().execute('''CREATE TABLE %s(round_id INTEGER, time STRING, num_servers INTEGER, exp_id INTEGER,  replication INTEGER, time_mw INTEGER,
            time_server INTEGER, time_queue INTEGER,
            time_wb_Queue INTEGER, is_read INTEGER, is_success INTEGER)''' % table_name_mw)
    conn.cursor().execute("drop table if exists %s" % table_name_resp)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, machine_id INTEGER, num_servers INTEGER,  replication INTEGER,
                op_id INTEGER, num_events INTEGER, data STRING)''' % table_name_resp)
    conn.commit()
    for filename in os.listdir(directory):
        match = p.match(filename)
        if match:
            machine_id = match.group(2)
            num_servers = match.group(1)
            exp_id = match.group(3)
            replication = match.group(4)
            data = extract_data(directory+filename)
            round = 1
            res = []
            for row in data.tolist():
                row.insert(0, float(replication))
                row.insert(0, float(num_servers))
                row.insert(0, float(machine_id))
                row.insert(0, float(round))
                row.insert(0, float(exp_id))
                round += 1
                temp = tuple([int(x) if x.is_integer() else float(x) for x in row])
                res.append(temp)
            c = conn.cursor()
            c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_client, res)
            conn.commit()

            res = []
            data_resp = extract_data_median_resp(directory + filename)
            for row in data_resp.tolist():
                op_id = row[0]
                num_events = row[1]
                del row[0]
                del row[1]
                data = ','.join([str(x) for x in row])
                res.append((exp_id, machine_id, num_servers, replication, op_id,  num_events, data))
            c = conn.cursor()
            c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?)' % table_name_resp, res)
            conn.commit()


        match = p_mw.match(filename)
        if match:
            num_servers = match.group(1)
            exp_id = match.group(2)
            replication = match.group(3)
            file = open(directory+filename, 'r')
            res = []
            round=1
            for line in file:
                splits = line.split(",")
                temp = (round, splits[0], num_servers, exp_id, replication, int(splits[1]), int(splits[2]),
                         int(splits[3]), int(splits[4]), int(splits[5]),int(splits[6]))
                res.append(temp)
                round += 1
            file.close()
            c = conn.cursor()
            c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?)' % table_name_mw, res)
            conn.commit()
    conn.close()

round_ref = re.compile('round(\d+)')
def move_client_data_to_db_writes(directory, db_name, table_name_client, table_name_mw, table_name_resp):
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_client)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, round_id INTEGER, machine_id INTEGER, num_servers INTEGER,  replication INTEGER, workload_id INTEGER,
        time INTEGER, ops INTEGER, tps INTEGER, net REAL, miss INTEGER, min INTEGER, max INTEGER, avg INTEGER,
         std REAL, geo REAL)''' % table_name_client)
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_mw)
    conn.cursor().execute('''CREATE TABLE %s(round_id INTEGER, time STRING, num_servers INTEGER, exp_id INTEGER,  replication INTEGER, workload_id INTEGER, time_mw INTEGER,
            time_server INTEGER, time_queue INTEGER,
            time_wb_Queue INTEGER, is_read INTEGER, is_success INTEGER)''' % table_name_mw)
    conn.cursor().execute("drop table if exists %s" % table_name_resp)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, machine_id INTEGER, num_servers INTEGER,  replication INTEGER, workload_id INTEGER,
                op_id INTEGER, num_events INTEGER, data STRING)''' % table_name_resp)
    conn.commit()

    for round_dir in os.listdir(directory):
        match_round_ref = round_ref.match(round_dir)
        if not match_round_ref:
            continue
        cur_directory = directory+round_dir+"/"
        for filename in os.listdir(cur_directory):
            match = p.match(filename)
            if match:
                machine_id = match.group(2)
                num_servers = match.group(1)
                exp_id = match_round_ref.group(1)
                workload_id = match.group(3)
                replication = match.group(4)
                data = extract_data(cur_directory+filename)
                round = 1
                res = []
                for row in data.tolist():
                    row.insert(0, float(workload_id))
                    row.insert(0, float(replication))
                    row.insert(0, float(num_servers))
                    row.insert(0, float(machine_id))
                    row.insert(0, float(round))
                    row.insert(0, float(exp_id))
                    round += 1
                    temp = tuple([int(x) if x.is_integer() else float(x) for x in row])
                    res.append(temp)
                c = conn.cursor()
                c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_client, res)
                conn.commit()

                continue

                res = []
                data_resp = extract_data_median_resp(cur_directory + filename)
                for row in data_resp.tolist():
                    op_id = row[0]
                    num_events = row[1]
                    del row[0]
                    del row[1]
                    data = ','.join([str(x) for x in row])
                    res.append((exp_id, machine_id, num_servers, replication, workload_id, op_id,  num_events, data))
                c = conn.cursor()
                c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?)' % table_name_resp, res)
                conn.commit()


            match = p_mw.match(filename)
            if match:
                num_servers = match.group(1)
                exp_id = match_round_ref.group(1)
                workload_id = match.group(2)
                replication = match.group(3)
                file = open(cur_directory+filename, 'r')
                res = []
                round=1
                for line in file:
                    splits = line.split(",")
                    temp = (round, splits[0], num_servers, exp_id, replication, workload_id, int(splits[1]), int(splits[2]),
                             int(splits[3]), int(splits[4]), int(splits[5]),int(splits[6]))
                    res.append(temp)
                    round += 1
                file.close()
                c = conn.cursor()
                c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_mw, res)
                conn.commit()
    conn.close()

def move_client_data_to_db_writes_seperat(directory, db_name, table_name_client):
    conn = sqlite3.connect(db_name)
    conn.cursor().execute("drop table if exists %s" % table_name_client)
    conn.cursor().execute('''CREATE TABLE %s(exp_id INTEGER, round_id INTEGER, machine_id INTEGER, num_servers INTEGER,  replication INTEGER, workload_id INTEGER,
        is_get INTEGER, time INTEGER, ops INTEGER, tps INTEGER, net REAL, miss INTEGER, min INTEGER, max INTEGER, avg INTEGER,
         std REAL, geo REAL)''' % table_name_client)

    for round_dir in os.listdir(directory):
        match_round_ref = round_ref.match(round_dir)
        if not match_round_ref:
            continue
        cur_directory = directory+round_dir+"/"
        for filename in os.listdir(cur_directory):
            match = p.match(filename)
            if match:
                machine_id = match.group(2)
                num_servers = match.group(1)
                exp_id = match_round_ref.group(1)
                workload_id = match.group(3)
                replication = match.group(4)
                dataGet = extract_data_get(cur_directory+filename)
                dataSet = extract_data_set(cur_directory+filename)
                round = 1
                res = []
                for row in dataGet.tolist():
                    row.insert(0, float(1))
                    row.insert(0, float(workload_id))
                    row.insert(0, float(replication))
                    row.insert(0, float(num_servers))
                    row.insert(0, float(machine_id))
                    row.insert(0, float(round))
                    row.insert(0, float(exp_id))
                    round += 1
                    temp = tuple([int(x) if x.is_integer() else float(x) for x in row])
                    res.append(temp)
                c = conn.cursor()
                c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_client, res)

                res = []
                round = 1
                for row in dataSet.tolist():
                    row.insert(0, float(0))
                    row.insert(0, float(workload_id))
                    row.insert(0, float(replication))
                    row.insert(0, float(num_servers))
                    row.insert(0, float(machine_id))
                    row.insert(0, float(round))
                    row.insert(0, float(exp_id))
                    round += 1
                    temp = tuple([int(x) if x.is_integer() else float(x) for x in row])
                    res.append(temp)

                c = conn.cursor()
                c.executemany('INSERT INTO %s VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)' % table_name_client, res)
                conn.commit()


    conn.close()




#move_client_data_to_db("../data/longrun/", "longrun.db", "longrun", "longrunb")
#move_client_data_to_db("../data/maxtpexp/", "maxtpexp.db", "maxtpexp_c", "maxtpexp_mw")
#res = extract_data_median_resp("../data/repexp/clientlog_3-0-1-1.txt")
#i = 1
#a = extract_data("clientlog_3-0-1-1.txt")
