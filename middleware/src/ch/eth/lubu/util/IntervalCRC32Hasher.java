package ch.eth.lubu.util;

import ch.eth.lubu.messages.IPartitionFunction;

import java.util.zip.CRC32;

/**
 * Created by lubu on 10.10.16.
 *
 * The load balancing with CRC32
 */
public class IntervalCRC32Hasher implements IPartitionFunction {

    private static final long max_num = 1L<<32;

    @Override
    public int hashToPartition(int numPartitions, String key) {
        long interval, hash, res;
        CRC32 crc32 = new CRC32();
        crc32.update(key.getBytes());
        hash = crc32.getValue();
        interval = max_num/numPartitions;
        res = (hash/interval) % numPartitions;
        return (int) res;
    }
}
