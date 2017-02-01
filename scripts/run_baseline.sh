USER_MACHINES="burlukas"
CLIENT_MACHINES="burlukasforaslvms1.westeurope.cloudapp.azure.com burlukasforaslvms2.westeurope.cloudapp.azure.com"
SERVER_MACHINE="burlukasforaslvms3.westeurope.cloudapp.azure.com"
SERVER_MACHINE_P="10.0.0.10"
INSTALL=0
SERVER_PORT=11560


#INSTALL
if [ $INSTALL = 1 ]
then
	for client_machine in $CLIENT_MACHINES
	do
		scp intstallMemslap.sh $USER_MACHINES@$client_machine:
		ssh -t $USER_MACHINES@$client_machine  "./intstallMemslap.sh"
		scp ../memaslap-workloads/smallvalue.cfg $USER_MACHINES@$client_machine:
	done 

	ssh -t $USER_MACHINES@$SERVER_MACHINE "sudo apt-get update && sudo apt-get install build-essential libevent-dev memcached screen"
fi

pidserver=()
echo "memcached -p $SERVER_PORT -t 1"
ssh $USER_MACHINES@$SERVER_MACHINE "memcached -p $SERVER_PORT -t 1" &
pidserver+=($!)

sleep 5

for ROUND in {1,2,3,4,5}
do
	# for NUM_CLIENTS in {4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64}
	for NUM_CLIENTS in {1,2,6,10,14,18,22}
	do
		waiting=()
		COUNTER=0
		for client_machine in $CLIENT_MACHINES
		do
			echo "Start Experiment with $NUM_CLIENTS per machine"
			echo "./libmemcached-1.0.18/clients/memaslap -s $SERVER_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -o 0.9 -S 1s -t 60s -F smallvalue.cfg"
			ssh $USER_MACHINES@$client_machine "./libmemcached-1.0.18/clients/memaslap -s $SERVER_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -o 0.9 -S 1s -t 60s -F smallvalue.cfg > clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt" &
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
			scp $USER_MACHINES@$client_machine:./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt ../data/baseline/
			ssh $USER_MACHINES@$client_machine "rm ./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt"
			COUNTER=$((COUNTER+1))
		done 
	done
done

pid=$(ssh $USER_MACHINES@$SERVER_MACHINE "pidof memcached 2>&1")
ssh $USER_MACHINES@$SERVER_MACHINE "sudo kill $pid"
