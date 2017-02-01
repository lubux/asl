package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.*;
import ch.eth.lubu.messages.HeaderMessageParser;
import ch.eth.lubu.util.TimeLogger;

/**
 * Created by lubu on 29.09.16.
 */
public class ClientProcessingFactory implements IMessageFunctionsFactory {

    private IMessageProcessor processor;

    public ClientProcessingFactory(IMessageProcessor processor) {
        this.processor = processor;
    }

    @Override
    public IMessageWriter getWriter() {
        IMessageWriter out = new DefaultMessageWriter();
        out.addMessageSendListener(new TimeLogger());
        return out;
    }

    @Override
    public IMessageParser getParser() {
        return new HeaderMessageParser(true);
    }

    @Override
    public IMessageProcessor getProcessor() {
        return processor;
    }
}
