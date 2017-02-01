package ch.eth.lubu.util;

import ch.eth.lubu.messages.IPartitionFunction;

import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * Created by lubu on 01.10.16.
 */
public class IntervalMD5Hasher implements IPartitionFunction {

    private static BigInteger max = BigInteger.ONE.shiftLeft(128);

    @Override
    public int hashToPartition(int numPartitions, String key) {
        MessageDigest m = null;
        try {
            m = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            return 0;
        }
        m.reset();
        m.update(key.getBytes());
        byte[] digest = m.digest();
        BigInteger number = new BigInteger(1,digest);
        BigInteger interval = max.divide(BigInteger.valueOf(numPartitions));
        int res = number.divide(interval).intValue();
        if(res>=numPartitions)
            res = numPartitions-1;
        return res;
    }
}
