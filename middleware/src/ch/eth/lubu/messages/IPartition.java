package ch.eth.lubu.messages;

/**
 * Created by lubu on 29.09.16.
 */
public interface IPartition {

    public int getID();

    public void putWriteQueue(MemcacheJob job);

    public void putReadQueue(MemcacheJob job);


}
