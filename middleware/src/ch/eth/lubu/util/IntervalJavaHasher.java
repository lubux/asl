package ch.eth.lubu.util;

import ch.eth.lubu.messages.IPartitionFunction;

/**
 * Created by lubu on 01.10.16.
 */
public class IntervalJavaHasher implements IPartitionFunction {



    @Override
    public int hashToPartition(int numPartitions, String key) {
        long hash = ((long)key.hashCode()) - ((long)Integer.MIN_VALUE);
        long interval = (1L<<32)/numPartitions;
        int res = (int) (hash/interval);
        if(res>=numPartitions)
            res = numPartitions-1;
        return res;
    }
}
