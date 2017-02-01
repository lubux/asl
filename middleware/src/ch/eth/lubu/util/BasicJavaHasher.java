package ch.eth.lubu.util;

import ch.eth.lubu.messages.IPartitionFunction;

/**
 * Created by lubu on 29.09.16.
 */
public class BasicJavaHasher implements IPartitionFunction {

    @Override
    public int hashToPartition(int numPartitions, String key) {
        return key.hashCode() % numPartitions;
    }
}
