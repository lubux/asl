package ch.eth.lubu.messages;

/**
 * Created by lubu on 29.09.16.
 */
public interface IPartitionFunction {

    public int hashToPartition(int numPartitions, String key);

}
