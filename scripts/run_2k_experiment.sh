USER_MACHINES="burlukas"
CLIENT_MACHINES="burlukasforaslvms1.westeurope.cloudapp.azure.com burlukasforaslvms2.westeurope.cloudapp.azure.com burlukasforaslvms3.westeurope.cloudapp.azure.com"
SERVER_MACHINES="burlukasforaslvms4.westeurope.cloudapp.azure.com burlukasforaslvms5.westeurope.cloudapp.azure.com burlukasforaslvms6.westeurope.cloudapp.azure.com burlukasforaslvms7.westeurope.cloudapp.azure.com burlukasforaslvms8.westeurope.cloudapp.azure.com burlukasforaslvms9.westeurope.cloudapp.azure.com burlukasforaslvms10.westeurope.cloudapp.azure.com"
MW_MACHINE="burlukasforaslvms11.westeurope.cloudapp.azure.com"
MW_MACHINE_P="10.0.0.8"
SERVER_PORT=11500
SERVER_MACHINE_P="10.0.0.9:$SERVER_PORT 10.0.0.5:$SERVER_PORT 10.0.0.6:$SERVER_PORT 10.0.0.14:$SERVER_PORT 10.0.0.12:$SERVER_PORT 10.0.0.7:$SERVER_PORT 10.0.0.11:$SERVER_PORT"
INSTALL=0
NUM_MINUTES="3m"
LOG_ITER="1s"
NUM_READER_THREADS=16
NUM_CLIENTS=64

OUTPUT_DIR="2kexp"
WORKLOAD_FILES="2k_small.cfg 2k_large.cfg"
NUM_SERVERS=3

#INSTALL
if [ $INSTALL = 1 ]
then
	waiting_clients=()
	for client_machine in $CLIENT_MACHINES
	do
		scp intstallMemslap.sh $USER_MACHINES@$client_machine:
		ssh -t $USER_MACHINES@$client_machine  "./intstallMemslap.sh" &
		waiting_clients+=($!)
	done

	waiting_servers=()
	for server_machine in $SERVER_MACHINES
	do
		ssh -t $USER_MACHINES@$server_machine "sudo apt-get update && sudo apt-get -y install build-essential libevent-dev memcached screen" &
		waiting_servers+=($!)
	done

	for pid in "${waiting_clients[@]}"
	do
		echo "waiting clients installations"
		wait $pid
	done

	for pid in "${waiting_servers[@]}"
	do
		echo "waiting servers installations"
		wait $pid
	done

	#ssh -t $USER_MACHINES@$MW_MACHINE "sudo add-apt-repository ppa:webupd8team/java && sudo apt-get update && sudo apt-get install oracle-java8-installer screen htop"
	ant -f ../middleware/build.xml
	scp ../middleware/dist/middleware-burlukas.jar $USER_MACHINES@$MW_MACHINE:
fi

echo "copy workload files"
for client_machine in $CLIENT_MACHINES
do
	for file in $WORKLOAD_FILES
	do
		scp ../memaslap-workloads/$file $USER_MACHINES@$client_machine:
	done
done


for ROUND in {1,2,3,4,5}
do
	for REPLICATION in {1,$NUM_SERVERS}
	do
		WORKLOAD_COUNTER=1
		for WORKLOAD in $WORKLOAD_FILES
		do
			TEMP_P=""
			ITER=0
			for cur in $SERVER_MACHINE_P
			do
				if [ "$ITER" -eq "$NUM_SERVERS" ]
				then
					break
				fi
				TEMP_P="$TEMP_P $cur"
				ITER=$((ITER+1))
			done

			TEMP=""
			ITER=0
			for cur in $SERVER_MACHINES
			do
				if [ "$ITER" -eq "$NUM_SERVERS" ]
				then
					break
				fi
				TEMP="$TEMP $cur"
				ITER=$((ITER+1))
			done


			echo "Start memcached servers"
			pidservers=()
			for server_machine in $TEMP
			do
				echo "memcached -p $SERVER_PORT -t 1"
				ssh $USER_MACHINES@$server_machine "memcached -p $SERVER_PORT -t 1" &
				pidservers+=($!)
			done

			sleep 10

			echo "Run middleware"
			MW_COMMAND="java -jar ./middleware-burlukas.jar -l $MW_MACHINE_P -p $SERVER_PORT -t $NUM_READER_THREADS -r $REPLICATION -m $TEMP_P -k 2"
			echo $MW_COMMAND
			ssh -t $USER_MACHINES@$MW_MACHINE $MW_COMMAND &
			pid_mw=($!)

			sleep 5

			COUNTER=0
			waiting=()
			for client_machine in $CLIENT_MACHINES
			do
				echo "Start Experiment with $NUM_CLIENTS per machine"
				MEMASLAP_CMD="./libmemcached-1.0.18/clients/memaslap -s $MW_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -o 0.9 -S 1s -t $NUM_MINUTES -F $WORKLOAD > clientlog_$WORKLOAD_COUNTER-$COUNTER-$ROUND-$REPLICATION.txt"
				echo $MEMASLAP_CMD
				ssh $USER_MACHINES@$client_machine $MEMASLAP_CMD &
				waiting+=($!)
				COUNTER=$((COUNTER+1))
			done 

			for pid in "${waiting[@]}"
			do
				echo "waiting client $pid"
				wait $pid
			done

			echo "Copy data clients"
			COUNTER=0
			for client_machine in $CLIENT_MACHINES
			do
				scp $USER_MACHINES@$client_machine:clientlog_$WORKLOAD_COUNTER-$COUNTER-$ROUND-$REPLICATION.txt ../data/$OUTPUT_DIR/
				ssh $USER_MACHINES@$client_machine "rm clientlog_$WORKLOAD_COUNTER-$COUNTER-$ROUND-$REPLICATION.txt"
				COUNTER=$((COUNTER+1))
			done

			echo "kill middleware"
      		pidm=$(ssh $USER_MACHINES@$MW_MACHINE "pidof java")
      		ssh $USER_MACHINES@$MW_MACHINE "sudo kill $pidm"

			echo "copy data from middleware"
			MIDDLEWARENAME="./mw_$WORKLOAD_COUNTER-$ROUND-$REPLICATION.log"
			ssh $USER_MACHINES@$MW_MACHINE "mv ./mw.log $MIDDLEWARENAME"
			scp $USER_MACHINES@$MW_MACHINE:$MIDDLEWARENAME ../data/$OUTPUT_DIR/
			ssh $USER_MACHINES@$MW_MACHINE "rm $MIDDLEWARENAME"

			
			echo "Stop memcached servers"
			for server_machine in $TEMP
			do
				pid=$(ssh $USER_MACHINES@$server_machine "pidof memcached 2>&1")
				ssh -t $USER_MACHINES@$server_machine "sudo kill $pid"
			done

			WORKLOAD_COUNTER=$((WORKLOAD_COUNTER+1))
		done
	done
	#Send Info experiment finished
	#telegram-cli -W -e "msg Lubu 'Replication Experiment Round $ROUND Finished'" &
done

for server_machine in $SERVER_MACHINES
do
	ssh-keygen -f "/home/lubu/.ssh/known_hosts" -R $server_machine
done

for client_machine in $CLIENT_MACHINES
do
	ssh-keygen -f "/home/lubu/.ssh/known_hosts" -R $client_machine
done

ssh-keygen -f "/home/lubu/.ssh/known_hosts" -R $client_machine


#Send Info experiment finished
#telegram-cli -W -e "msg Lubu 'Replication Experiment Finished'"
