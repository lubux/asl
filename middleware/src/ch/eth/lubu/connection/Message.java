package ch.eth.lubu.connection;

import ch.eth.lubu.util.TimeTracker;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by lubu on 27.09.16.
 */
public class Message {

    private int connID;

    protected IMemManager manager;
    protected List<MemoryBlock> blocks = new ArrayList<>();
    protected int lenMsg = 0;
    protected int curBlockId = 0;
    protected int blockOffset = 0;

    public TimeTracker tracker = null;

    private boolean exists = true;

    public Message(int conn, IMemManager manager) {
        this.connID = conn;
        this.manager = manager;
        allocBlocks(1);
    }

    protected void allocBlocks(int numBlocks) {
        for (int i=0; i<numBlocks; i++) {
            blocks.add(manager.getBlock());
        }
    }

    public void writeByte(byte dataByte) {
        if(blockOffset >= manager.getBlockSoze()) {
            allocBlocks(1);
            blockOffset = 1;
            curBlockId++;
            blocks.get(curBlockId).buffer[0] = dataByte;
        } else {
            blocks.get(curBlockId).buffer[blockOffset] = dataByte;
            blockOffset++;
        }
        lenMsg++;
    }


    public void writeData(byte[] inData) {
        int newLength = inData.length + lenMsg;
        int bSize = manager.getBlockSoze();
        int totLen = bSize *blocks.size();
        int curPos = 0, numBlocks;
        if(newLength > totLen) {
            numBlocks = (newLength - totLen)/bSize + 1;
            allocBlocks(numBlocks);
            for(int iter=0; iter<numBlocks; iter++) {
                MemoryBlock curBlock = blocks.get(curBlockId);
                System.arraycopy(inData, curPos, curBlock.buffer, blockOffset, bSize - blockOffset);
                curPos += bSize - blockOffset;
                blockOffset = 0;
                curBlockId++;
            }
            MemoryBlock last = blocks.get(curBlockId);
            blockOffset = inData.length - curPos;
            System.arraycopy(inData, curPos, last.buffer, 0, blockOffset);
        } else {
            System.arraycopy(inData, 0, blocks.get(curBlockId).buffer, blockOffset, inData.length);
            blockOffset += inData.length;
        }
        lenMsg = bSize * (blocks.size()-1) + blockOffset;
    }

    private int write(ByteBuffer byteBuffer, int numBytes) {
        if(!exists)
            throw new RuntimeException("Cannot write data on freed message");
        int newLength = numBytes + lenMsg;
        int bSize = manager.getBlockSoze();
        int totLen = bSize *blocks.size();
        int curPos = 0, numBlocks;
        if(newLength > totLen) {
            numBlocks = (newLength - totLen)/bSize + 1;
            allocBlocks(numBlocks);
            for(int iter=0; iter<numBlocks; iter++) {
                MemoryBlock curBlock = blocks.get(curBlockId);
                byteBuffer.get(curBlock.buffer, blockOffset, bSize - blockOffset);
                curPos += bSize - blockOffset;
                blockOffset = 0;
                curBlockId++;
            }
            MemoryBlock last = blocks.get(curBlockId);
            blockOffset = numBytes - curPos;
            byteBuffer.get(last.buffer, 0, blockOffset);
        } else {
            byteBuffer.get(blocks.get(curBlockId).buffer, blockOffset, numBytes);
            blockOffset += numBytes;
        }
        lenMsg = bSize * (blocks.size()-1) + blockOffset;
        return numBytes;
    }

    public int writeData(ByteBuffer byteBuffer) {
        return write(byteBuffer, byteBuffer.remaining());
    }

    public int writeData(ByteBuffer byteBuffer, int maxNumBytes) {
        if(!exists)
            throw new RuntimeException("Cannot write data on freed message");
        int numBytes = byteBuffer.remaining();
        numBytes = Math.min(maxNumBytes, numBytes);
        return write(byteBuffer, numBytes);
    }

    public void transferData(ByteBuffer buff, int from, int len) {
        int blockFrom = from / this.manager.getBlockSoze();
        int blockTo = (from + len) / this.manager.getBlockSoze();
        int blockOff = from % this.manager.getBlockSoze();
        int blockToOff = (from + len) % this.manager.getBlockSoze();
        for (int iter=blockFrom; iter<blockTo; iter++) {
            buff.put(blocks.get(iter).buffer, blockOff, this.manager.getBlockSoze() - blockOff);
            blockOff = 0;
        }
        buff.put(blocks.get(blockTo).buffer, blockOff, blockToOff);
    }

    public void transferData(OutputStream stream) throws IOException {
        for(int blockIter=0; blockIter<blocks.size()-1; blockIter++) {
            stream.write(blocks.get(blockIter).buffer);
        }
        stream.write(blocks.get(blocks.size()-1).buffer, 0, blockOffset);
    }

    public int getConn() {
        return connID;
    }

    public void close() {
        exists = false;
        for(MemoryBlock block : blocks)
            manager.freeBlock(block);
    }

    public int getLen() {
        return lenMsg;
    }

    public void setConnID(int connID) {
        this.connID = connID;
    }

    public int getNumAllocatedBlocks() {
        return blocks.size();
    }

    public byte[] getAsByteArray() {
        byte[] msg = new byte[lenMsg];
        int curPtr = 0;
        for(int blockIter=0; blockIter<blocks.size()-1; blockIter++) {
            int len = blocks.get(blockIter).buffer.length;
            System.arraycopy(blocks.get(blockIter).buffer, 0, msg, curPtr, len);
            curPtr += len;
        }
        System.arraycopy(blocks.get(blocks.size()-1).buffer, 0, msg, curPtr, blockOffset);
        return msg;
    }
}
