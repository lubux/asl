package ch.eth.lubu.connection;

import java.io.Closeable;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SocketChannel;

/**
 * Created by lubu on 27.09.16.
 */
public class Connection implements Closeable {

    private int connectionID;

    private SocketChannel channel;

    private boolean connAlive = true;

    private IMessageParser messageParser;
    private IMessageWriter messageWriter;

    public Connection(int connectionID, SocketChannel channel, IMessageParser messageParser, IMessageWriter messageWriter) {
        this.connectionID = connectionID;
        this.channel = channel;
        this.messageParser = messageParser;
        this.messageWriter = messageWriter;
    }

    public SocketChannel getChannel() {
        return channel;
    }

    public boolean isAlive() {
        return connAlive;
    }

    public int getConnectionID() {
        return connectionID;
    }

    public int readData(ByteBuffer buffer) throws IOException {
        int len, res = 0;
        len = channel.read(buffer);
        res += len;
        while (len > 0 && buffer.hasRemaining()) {
            len = channel.read(buffer);
            res += len;
        }
        this.connAlive = res != -1;
        return res;
    }

    public int writeData(ByteBuffer buffer) throws IOException {
        int len, res = 0;
        len = channel.write(buffer);
        res += len;
        while (len > 0 && buffer.hasRemaining()) {
            len = channel.write(buffer);
            res += len;
        }
        this.connAlive = res != -1;
        return res;
    }

    public IMessageParser getMessageParser() {
        return messageParser;
    }

    public IMessageWriter getMessageWriter() {
        return messageWriter;
    }

    @Override
    public void close() throws IOException {
        channel.close();
    }
}
