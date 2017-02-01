package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.AsyncConnectionManager;
import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.messages.IPartitionFunction;
import ch.eth.lubu.messages.Partitioner;

import java.io.IOException;

/**
 * Created by lubu on 29.09.16.
 *
 * The main class implementing the middleware
 */
public class Middleware {

    private ProcessingPartition[] processingPartitions;
    private ClientProcessor processor;

    /**
     *
     * @param myIP ip
     * @param localPort port
     * @param memcacheServerIPs ips
     * @param portServers server ports
     * @param numConnections number of synchronous connections per partition
     * @param numReaderThreads number of reader threads per partition
     * @param rangeWrite the replication factor
     * @param numWriteServerConnectionPools number of asny connection pools
     * @param numBackWriters  number of write back client threads
     * @param manager memory manager
     * @param func hash function
     * @throws IOException
     */
    public Middleware(String myIP, int localPort, String[] memcacheServerIPs, int[] portServers, int numConnections, int numReaderThreads, int rangeWrite, int numWriteServerConnectionPools, int numBackWriters, IMemManager manager, IPartitionFunction func) throws IOException {
        AsyncConnectionManager[] asyncConnectionManagers= new AsyncConnectionManager[numWriteServerConnectionPools];
        for(int iter=0; iter<asyncConnectionManagers.length; iter++) {
            asyncConnectionManagers[iter] = new AsyncConnectionManager(memcacheServerIPs,
                    portServers,
                    new ServerProcessingFactory(),
                    manager);
        }
        processingPartitions = new ProcessingPartition[memcacheServerIPs.length];
        for(int iter=0; iter<memcacheServerIPs.length; iter++) {
            processingPartitions[iter] = new ProcessingPartition(iter,
                    memcacheServerIPs[iter],
                    portServers[iter],
                    asyncConnectionManagers[iter % asyncConnectionManagers.length],
                    numConnections,
                    numReaderThreads,
                    rangeWrite,
                    manager);
        }

        Partitioner partitioner = new Partitioner(processingPartitions, func);
        ClientProcessingFactory factory = new ClientProcessingFactory(partitioner);
        processor = new ClientProcessor(myIP, localPort, factory,manager, numBackWriters);
    }

    public void start() {
        for(int iter=0; iter<processingPartitions.length; iter++) {
            processingPartitions[iter].start();
        }
        processor.start();
    }

    public void stop() {
        for(int iter=0; iter<processingPartitions.length; iter++) {
            processingPartitions[iter].stop();
        }
        processor.stop();
    }

}
