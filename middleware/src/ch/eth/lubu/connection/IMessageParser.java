package ch.eth.lubu.connection;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.List;

/**
 * Created by lubu on 28.09.16.
 */
public interface IMessageParser {


    public void setMemoryManager(IMemManager man);

    public void read(Connection connection, ByteBuffer byteBuffer) throws IOException;

    public List<Message> getMessages();



}
