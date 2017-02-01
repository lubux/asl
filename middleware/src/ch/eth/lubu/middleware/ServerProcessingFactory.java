package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.*;
import ch.eth.lubu.messages.HeaderMessageParser;

/**
 * Created by lubu on 29.09.16.
 */
public class ServerProcessingFactory implements IMessageFunctionsFactory {
    @Override
    public IMessageWriter getWriter() {
        return new DefaultMessageWriter();
    }

    @Override
    public IMessageParser getParser() {
        return new HeaderMessageParser(false);
    }

    @Override
    public IMessageProcessor getProcessor() {
        return null;
    }
}
