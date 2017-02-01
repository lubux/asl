package ch.eth.lubu.messages;

import ch.eth.lubu.connection.WriteBack;

/**
 * Created by lubu on 29.09.16.
 */
public class MemcacheJob {

    private int partitionID;
    private WriteBack back;
    private Request request;

    public MemcacheJob(int partitionID, WriteBack back, Request request) {
        this.back = back;
        this.request = request;
        this.partitionID = partitionID;
    }

    public WriteBack getBack() {
        return back;
    }

    public Request getRequest() {
        return request;
    }

    public int getPartitionID() {
        return partitionID;
    }
}
