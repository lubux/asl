USER_MACHINES="burlukas"
CLIENT_MACHINES="burlukasforaslvms1.westeurope.cloudapp.azure.com burlukasforaslvms2.westeurope.cloudapp.azure.com burlukasforaslvms3.westeurope.cloudapp.azure.com"
SERVER_MACHINES="burlukasforaslvms5.westeurope.cloudapp.azure.com burlukasforaslvms6.westeurope.cloudapp.azure.com burlukasforaslvms7.westeurope.cloudapp.azure.com"
MW_MACHINE="burlukasforaslvms4.westeurope.cloudapp.azure.com"
MW_MACHINE_P="10.0.0.5"
SERVER_PORT=11560
SERVER_MACHINE_P="10.0.0.7:$SERVER_PORT 10.0.0.4:$SERVER_PORT 10.0.0.10:$SERVER_PORT"
INSTALL=0
NUM_READER_THREADS=16
REPLICATION=3
NUM_SECONDS_MW=4500
NUM_MINUTES="70m"
LOG_ITER="1s"
NUM_CLIENTS=64
ROUND=1

#INSTALL
if [ $INSTALL = 1 ]
then
	for client_machine in $CLIENT_MACHINES
	do
		scp intstallMemslap.sh $USER_MACHINES@$client_machine:
		ssh -t $USER_MACHINES@$client_machine  "./intstallMemslap.sh"
		scp ../memaslap-workloads/smallvalue.cfg $USER_MACHINES@$client_machine:
	done 

	for server_machine in $SERVER_MACHINES
	do
		ssh -t $USER_MACHINES@$server_machine "sudo apt-get update && sudo apt-get -y install build-essential libevent-dev memcached screen"
	done

	#ssh -t $USER_MACHINES@$MW_MACHINE "sudo add-apt-repository ppa:webupd8team/java && sudo apt-get update && sudo apt-get install oracle-java8-installer screen htop"
	ant -f ../middleware/build.xml
	scp ../middleware/dist/middleware-burlukas.jar $USER_MACHINES@$MW_MACHINE:
fi

pidservers=()
for server_machine in $SERVER_MACHINES
do
	echo "memcached -p $SERVER_PORT -t 1"
	ssh $USER_MACHINES@$server_machine "memcached -p $SERVER_PORT -t 1" &
	pidservers+=($!)
done

sleep 5

echo "Run middleware"
echo "java -jar ./middleware-burlukas.jar -l $MW_MACHINE_P -p $SERVER_PORT -t $NUM_READER_THREADS -r $REPLICATION -m $SERVER_MACHINE_P -e 1 -d $NUM_SECONDS_MW > mw.log"
ssh -t $USER_MACHINES@$MW_MACHINE "java -jar ./middleware-burlukas.jar -l $MW_MACHINE_P -p $SERVER_PORT -t $NUM_READER_THREADS -r $REPLICATION -m $SERVER_MACHINE_P -e 1 -d $NUM_SECONDS_MW -k 2 > mw.log" &
pid_mw=($!)

sleep 5

waiting=()
COUNTER=0
for client_machine in $CLIENT_MACHINES
do
	echo "Start Experiment with $NUM_CLIENTS per machine"
	echo "./libmemcached-1.0.18/clients/memaslap -s $MW_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -o 0.9 -S $LOG_ITER -t $NUM_MINUTES -F smallvalue.cfg > clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt"
	ssh $USER_MACHINES@$client_machine "./libmemcached-1.0.18/clients/memaslap -s $MW_MACHINE_P:$SERVER_PORT -T $NUM_CLIENTS -c $NUM_CLIENTS -o 0.9 -S $LOG_ITER -t $NUM_MINUTES -F smallvalue.cfg > clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt" &
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
	scp $USER_MACHINES@$client_machine:./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt ../data/longrun/
	ssh $USER_MACHINES@$client_machine "rm ./clientlog_$NUM_CLIENTS-$COUNTER-$ROUND.txt"
	COUNTER=$((COUNTER+1))
done 

echo "wait middleware"
wait $pid_mw

scp $USER_MACHINES@$MW_MACHINE:./mw.log ../data/longrun/
ssh $USER_MACHINES@$MW_MACHINE "rm ./mw.log"

for server_machine in $SERVER_MACHINES
do
	pid=$(ssh $USER_MACHINES@$server_machine "pidof memcached 2>&1")
	ssh -t $USER_MACHINES@$server_machine "sudo kill $pid"
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
