USER_MACHINES="burlukas"
CLIENT_MACHINES="burlukasforaslvms1.westeurope.cloudapp.azure.com burlukasforaslvms2.westeurope.cloudapp.azure.com burlukasforaslvms3.westeurope.cloudapp.azure.com burlukasforaslvms4.westeurope.cloudapp.azure.com burlukasforaslvms5.westeurope.cloudapp.azure.com"
SERVER_MACHINES="burlukasforaslvms6.westeurope.cloudapp.azure.com burlukasforaslvms7.westeurope.cloudapp.azure.com burlukasforaslvms8.westeurope.cloudapp.azure.com burlukasforaslvms9.westeurope.cloudapp.azure.com burlukasforaslvms10.westeurope.cloudapp.azure.com"
MW_MACHINE="burlukasforaslvms11.westeurope.cloudapp.azure.com"
MW_MACHINE_P="10.0.0.13"
SERVER_PORT=11500
SERVER_MACHINE_P="10.0.0.12:$SERVER_PORT 10.0.0.7:$SERVER_PORT 10.0.0.10:$SERVER_PORT 10.0.0.4:$SERVER_PORT 10.0.0.5:$SERVER_PORT"
INSTALL=0
REPLICATION=1
#NUM_SECONDS_MW=600
NUM_MINUTES="3m"
LOG_ITER="1s"

OUTPUT_DIR="maxtpexp"
WORKLOAD_FILE="maxtpworkload.cfg"


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
		scp ../memaslap-workloads/$WORKLOAD_FILE $USER_MACHINES@$client_machine:
	done



for ROUND in {1,}
do
	# for NUM_CLIENTS in {4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64}
	for NUM_CLIENTS in {80,90}
	do
		for NUM_READER_THREADS in {16,}
			do
				waiting=()
				COUNTER=0

				echo "Start memcached servers"
				pidservers=()
				for server_machine in $SERVER_MACHINES
				do
					echo "memcached -p $SERVER_PORT -t 1"
					ssh $USER_MACHINES@$server_machine "memcached -p $SERVER_PORT -t 1" &
					pidservers+=($!)
				done

				sleep 10

				echo "Run middleware"
				MW_COMMAND="java -jar ./middleware-burlukas.jar -l $MW_MACHINE_P -p $SERVER_PORT -t $NUM_READER_THREADS -r $REPLICATION -m $SERVER_MACHINE_P -k 2"
				echo $MW_COMMAND
				ssh -t $USER_MACHINES@$MW_MACHINE $MW_COMMAND &
				pid_mw=($!)

				sleep 5

				for client_machine in $CLIENT_MACHINES
				do
					echo "Start Experiment with $NUM_CLIENTS per machine"
					MEMASLAP_CMD="./libmemcached-1.0.18/clients/memaslap -s $MW_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -w 1k -o 0.9 -S 1s -t $NUM_MINUTES -F $WORKLOAD_FILE > clientlog_$NUM_CLIENTS-$COUNTER-$ROUND-$NUM_READER_THREADS.txt"
					echo $MEMASLAP_CMD
					ssh $USER_MACHINES@$client_machine $MEMASLAP_CMD &
					waiting+=($!)
					COUNTER=$((COUNTER+1))
				done 

				for pid in "${waiting[@]}"
				do
					echo "waiting"
					wait $pid
				done

				COUNTER=0
				for client_machine in $CLIENT_MACHINES
				do
					scp $USER_MACHINES@$client_machine:./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND-$NUM_READER_THREADS.txt ../data/$OUTPUT_DIR/
					ssh $USER_MACHINES@$client_machine "rm ./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND-$NUM_READER_THREADS.txt"
					COUNTER=$((COUNTER+1))
				done 

				echo "kill middleware"
      			pidm=$(ssh $USER_MACHINES@$MW_MACHINE "pidof java")
      			ssh $USER_MACHINES@$MW_MACHINE "sudo kill $pidm"

				echo "copy data from middleware"
				ssh $USER_MACHINES@$MW_MACHINE "mv ./mw.log ./mw_$NUM_CLIENTS-$ROUND-$NUM_READER_THREADS.log"
				scp $USER_MACHINES@$MW_MACHINE:./mw_$NUM_CLIENTS-$ROUND-$NUM_READER_THREADS.log ../data/$OUTPUT_DIR/
				ssh $USER_MACHINES@$MW_MACHINE "rm ./mw_$NUM_CLIENTS-$ROUND-$NUM_READER_THREADS.log"

				echo "Stop memcached servers"
				for server_machine in $SERVER_MACHINES
				do
					pid=$(ssh $USER_MACHINES@$server_machine "pidof memcached 2>&1")
					ssh -t $USER_MACHINES@$server_machine "sudo kill $pid"
				done

		done
	done
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
telegram-cli -W -e "msg Lubu 'Expensive Max Througput Experiment Finished'"
