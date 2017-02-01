package ch.eth.lubu.connection;

/**
 * Created by lubu on 28.09.16.
 */
public interface IMessageFunctionsFactory {

    public IMessageWriter getWriter();

    public IMessageParser getParser();

    public IMessageProcessor getProcessor();

}
