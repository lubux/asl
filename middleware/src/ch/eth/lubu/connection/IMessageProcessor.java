package ch.eth.lubu.connection;

/**
 * Created by lubu on 28.09.16.
 */
public interface IMessageProcessor {

    public void processMessage(Message m, WriteBack backWrite);

}
