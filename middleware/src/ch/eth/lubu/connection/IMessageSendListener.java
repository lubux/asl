package ch.eth.lubu.connection;

/**
 * Created by lubu on 10.10.16.
 */
public interface IMessageSendListener {

    public void onMessageSended(Message m);

    public void onMessageDequeued(Message m);

}
