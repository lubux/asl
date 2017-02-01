package ch.eth.lubu.util;

import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.connection.MemoryBlock;

/**
 * Created by lubu on 28.09.16.
 *
 * A basic memory manager that just allocates a buffer
 * with a fixed size.
 * Free has no effect just garbage collection
 */
public class DumbMemoryManager implements IMemManager {

    private int size;

    public DumbMemoryManager(int size) {
        this.size = size;
    }

    @Override
    public MemoryBlock getBlock() {
        return new MemoryBlock(0, new byte[size]);
    }

    @Override
    public void freeBlock(MemoryBlock block) {
        // nothing gb
    }

    @Override
    public int getBlockSoze() {
        return size;
    }

}
