package ch.eth.lubu.connection;

/**
 * Created by lubu on 28.09.16.
 */
public interface IMemManager {

    public MemoryBlock getBlock();

    public void freeBlock(MemoryBlock block);

    public int getBlockSoze();

}
