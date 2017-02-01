package ch.eth.lubu.messages;

import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.connection.MemoryBlock;
import ch.eth.lubu.connection.Message;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.nio.ByteBuffer;

/**
 * Created by lubu on 29.09.16.
 */
public abstract class HeaderMessage extends Message {

    private static final char L_DELIM = '\r';
    private static final char R_DELIM = '\n';

    public HeaderMessage(int conn, IMemManager manager) {
        super(conn, manager);
    }

    protected String[] header = null;
    protected int headerSize = -1;

    /**
     * Assumes HEADER ALWAYS fits in first block
     * @return
     */
    protected String[] getHeader() {
        byte[] data = blocks.get(0).buffer;
        if (header == null) {
            int offset = -1;
            char cur, next;

            if(lenMsg>0) {
                cur = (char) (data[0] & 0xFF);
            } else {
                return header;
            }

            for (int i=1; i<data.length; i++) {
                next = (char) (data[i] & 0xFF);
                if (cur == L_DELIM && next == R_DELIM) {
                    offset = i;
                    break;
                }
                cur = next;
            }

            if(offset == -1) {
                return header;
            }

            byte[] temp = new byte[offset + 1];
            System.arraycopy(data, 0, temp, 0, offset + 1);
            String tempStr = new String(temp);
            tempStr = tempStr.replace("\r\n", "");
            this.header = tempStr.split(" ");
            this.headerSize = offset + 1;
        }
        return header;
    }

    public int writeMaxUntilDelim(ByteBuffer byteBuffer) {
        int byteCounter = 0;
        boolean foundFirst = false;
        while(byteBuffer.hasRemaining()) {
            byte cur = byteBuffer.get();
            byteCounter++;
            if(blockOffset == manager.getBlockSoze()) {
                allocBlocks(1);
                curBlockId++;
                blockOffset = 0;
            }

            MemoryBlock block = blocks.get(curBlockId);
            block.buffer[blockOffset] = cur;
            blockOffset++;
            lenMsg++;

            if(foundFirst && ((cur & 0xFF) == R_DELIM)) {
                break;
            } else {
                foundFirst = (cur & 0xFF) == L_DELIM;
            }
        }
        return byteCounter;
    }

    public void readUntilDelim(BufferedInputStream in) throws IOException {
        int byteCounter = 0;
        boolean foundFirst = false;
        while(true) {
            byte cur = (byte) in.read();
            byteCounter++;
            if(blockOffset == manager.getBlockSoze()) {
                allocBlocks(1);
                curBlockId++;
                blockOffset = 0;
            }

            MemoryBlock block = blocks.get(curBlockId);
            block.buffer[blockOffset] = cur;
            blockOffset++;
            lenMsg++;

            if(foundFirst && ((cur & 0xFF) == R_DELIM)) {
                break;
            } else {
                foundFirst = (cur & 0xFF) == L_DELIM;
            }
        }
    }

    public boolean containsHeader() {
        return getHeader() != null;
    }

    public abstract boolean hasBody();

    public abstract int predictFullMessageLength();

    public abstract HeaderMessage createNew();

}
