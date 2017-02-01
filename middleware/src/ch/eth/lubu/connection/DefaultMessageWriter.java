package ch.eth.lubu.connection;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.Queue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * Created by lubu on 28.09.16.
 */
public class DefaultMessageWriter implements IMessageWriter {

    private Queue<Message> pendingMessages = new LinkedBlockingQueue<>();
    private Message curMessage = null;
    private int numBytesWritten = 0;

    private final Object mutex = new Object();

    private ArrayList<IMessageSendListener> listeners = new ArrayList<>();

    @Override
    public boolean hasMessages() {
        synchronized (mutex) {
            return !pendingMessages.isEmpty() || curMessage != null;
        }
    }

    @Override
    public void enqueueMsg(Message msg) {
        synchronized (mutex) {
            if (curMessage == null) {
                curMessage = msg;
                for(IMessageSendListener listener : listeners) {
                    listener.onMessageDequeued(curMessage);
                }
            } else {
                this.pendingMessages.add(msg);
            }
        }
    }

    @Override
    public boolean write(Connection conn, ByteBuffer buffer) throws IOException {
        boolean hasMore = false;
        int numBytes;
        buffer.clear();
        curMessage.transferData(buffer, this.numBytesWritten, curMessage.getLen() - this.numBytesWritten);
        buffer.flip();

        numBytes = conn.writeData(buffer);
        this.numBytesWritten += numBytes;

        if(this.numBytesWritten >= curMessage.getLen()) {
            curMessage.close();
            for(IMessageSendListener listener : listeners) {
                listener.onMessageSended(curMessage);
            }
            synchronized (mutex) {
                curMessage = pendingMessages.poll();
                if (curMessage != null) {
                    for (IMessageSendListener listener : listeners) {
                        listener.onMessageDequeued(curMessage);
                    }
                    hasMore = true;
                }
            }
            this.numBytesWritten = 0;
        }
        return hasMore;
    }

    @Override
    public void addMessageSendListener(IMessageSendListener listener) {
        listeners.add(listener);
    }

}
