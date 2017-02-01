package ch.eth.lubu.connection;

import java.io.IOException;
import java.nio.ByteBuffer;

/**
 * Created by lubu on 28.09.16.
 */
public interface IMessageWriter {

    public boolean hasMessages();

    public void enqueueMsg(Message msg);

    public boolean write(Connection conn, ByteBuffer buffer) throws IOException;

    public void addMessageSendListener(IMessageSendListener listener);


}
