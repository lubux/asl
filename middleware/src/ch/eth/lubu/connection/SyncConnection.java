package ch.eth.lubu.connection;

import java.io.*;
import java.net.Socket;

/**
 * Created by lubu on 29.09.16.
 */
public class SyncConnection implements Closeable {

    private int connectionID;

    private Socket channel;
    private ISyncMessageParser messageParser;

    private BufferedOutputStream outStream;
    private BufferedInputStream inReader;

    public SyncConnection(int connectionID, ISyncMessageParser messageParser, String ip, int port) throws IOException {
        this.connectionID = connectionID;
        this.messageParser = messageParser;
        channel = new Socket(ip, port);
        outStream = new BufferedOutputStream(channel.getOutputStream());
        inReader = new BufferedInputStream(channel.getInputStream());
    }

    public void writeMessage(Message msg) throws IOException {
        msg.transferData(outStream);
        outStream.flush();
    }

    public Message readMessage() throws IOException {
        return messageParser.readMessage(inReader);
    }

    public int getConnectionID() {
        return connectionID;
    }

    @Override
    public void close() throws IOException {
        outStream.close();
        inReader.close();
        channel.close();
    }
}
