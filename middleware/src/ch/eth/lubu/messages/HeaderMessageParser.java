package ch.eth.lubu.messages;

import ch.eth.lubu.connection.*;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by lubu on 28.09.16.
 *
 * Implements the message parsing for requests and server responses
 */
public class HeaderMessageParser implements IMessageParser, ISyncMessageParser {

    private IMemManager man;
    private List<Message> messages = new ArrayList<>();
    private HeaderMessage curMessage = null;
    private boolean forRequest;

    public HeaderMessageParser(boolean forRequest) {
        this.forRequest = forRequest;
    }

    @Override
    public void setMemoryManager(IMemManager man) {
        this.man = man;
        if(forRequest)
            this.curMessage = new Request(-1, man);
        else {
            this.curMessage = new Response(-1, man);
        }
    }

    @Override
    public void read(Connection connection, ByteBuffer byteBuffer) throws IOException {
        byteBuffer.clear();
        int numBytesRead = connection.readData(byteBuffer);
        int numBytesWrite = 0;

        if(numBytesRead==-1)
            return;

        byteBuffer.flip();

        curMessage.setConnID(connection.getConnectionID());
        while (numBytesRead > numBytesWrite) {
            if(!curMessage.containsHeader()) {
                numBytesWrite += curMessage.writeMaxUntilDelim(byteBuffer);
                continue;
            }

            if (curMessage.hasBody()) {
                int curLen = curMessage.getLen();
                int shouldLen = curMessage.predictFullMessageLength();

                if(shouldLen-curLen < numBytesRead-numBytesWrite) {
                    shouldLen = curMessage.predictFullMessageLength();
                    numBytesWrite += curMessage.writeData(byteBuffer, shouldLen-curLen);
                    messages.add(curMessage);
                    curMessage = curMessage.createNew();
                    curMessage.setConnID(connection.getConnectionID());
                } else {
                    numBytesWrite += curMessage.writeData(byteBuffer);
                }

            } else {
                messages.add(curMessage);
                curMessage = curMessage.createNew();
                curMessage.setConnID(connection.getConnectionID());
            }
        }
        if(curMessage.containsHeader()) {
            if (!curMessage.hasBody() ||
                    (curMessage.hasBody() && curMessage.predictFullMessageLength() == curMessage.getLen())) {
                messages.add(curMessage);
                curMessage = curMessage.createNew();
                curMessage.setConnID(connection.getConnectionID());
            }
        }
    }

    @Override
    public List<Message> getMessages() {
        return this.messages;
    }

    @Override
    public Message readMessage(BufferedInputStream reader) throws IOException {
        //hack maybe make nicer
        HeaderMessage msg;
        if(forRequest)
            msg = new Request(-1, man);
        else {
            msg = new Response(-1, man);
        }

        msg.readUntilDelim(reader);
        if(msg.hasBody()) {
            int toRead = msg.predictFullMessageLength() - msg.getLen();
            for(int i=0; i<toRead;i++) {
                msg.writeByte((byte) (reader.read()));
            }
        }
        return msg;
    }
}
