package ch.eth.lubu.messages;

import ch.eth.lubu.connection.IMessageProcessor;
import ch.eth.lubu.connection.Message;
import ch.eth.lubu.connection.ServerConnectionProcessor;
import ch.eth.lubu.connection.WriteBack;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements the loadbalancing  for incoming client requests
 *
 */
public class Partitioner implements IMessageProcessor {

    private static Logger log = LogManager.getLogger(ServerConnectionProcessor.class.getName());

    private IPartition[] partitions;
    private IPartitionFunction hasher;

    public Partitioner(IPartition[] partitions, IPartitionFunction hasher) {
        this.partitions = partitions;
        this.hasher = hasher;
    }

    @Override
    public void processMessage(Message m, WriteBack backWrite) {
        int partitionID;
        if(!(m instanceof Request))
            return;

        Request request = (Request) m;
        partitionID = hasher.hashToPartition(partitions.length, request.getKey());

        if(request.isWrite() || request.isDelete())
            partitions[partitionID].putWriteQueue(new MemcacheJob(partitionID, backWrite, request));
        else
            partitions[partitionID].putReadQueue(new MemcacheJob(partitionID, backWrite, request));

    }
}
