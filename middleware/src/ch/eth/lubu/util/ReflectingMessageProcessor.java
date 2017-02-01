package ch.eth.lubu.util;

import ch.eth.lubu.connection.IMessageProcessor;
import ch.eth.lubu.connection.Message;
import ch.eth.lubu.connection.WriteBack;

/**
 * Created by lubu on 28.09.16.
 */
public class ReflectingMessageProcessor implements IMessageProcessor {


    @Override
    public void processMessage(Message m, WriteBack backWrite) {
        System.out.println("Message Received from Connectiomn: " + m.getConn());

        Message response = backWrite.getEmptyMessage(m.getConn());
        response.writeData("Hello:)\n".getBytes());

        backWrite.enqueueMessage(response);
    }
}
