package ch.eth.lubu.connection;

/**
 * Created by lubu on 28.09.16.
 */
public class MemoryBlock {

    private int id;

    public byte[] buffer;

    public MemoryBlock(int id, byte[] buffer) {
        this.id = id;
        this.buffer = buffer;
    }

    public int getId() {
        return id;
    }

    public int getBlockSize() {
        return buffer.length;
    }
}
