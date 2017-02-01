package ch.eth.lubu.messages;

import ch.eth.lubu.connection.*;
import ch.eth.lubu.util.ReflectingMessageProcessor;

/**
 * Created by lubu on 28.09.16.
 */
public class MProcFactory implements IMessageFunctionsFactory {

    @Override
    public IMessageWriter getWriter() {
        return new DefaultMessageWriter();
    }

    @Override
    public IMessageParser getParser() {
        return new HeaderMessageParser(true);
    }

    @Override
    public IMessageProcessor getProcessor() {
        return new ReflectingMessageProcessor();
    }
}
