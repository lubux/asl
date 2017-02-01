package ch.eth.lubu.connection;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.IOException;

/**
 * Created by lubu on 29.09.16.
 */
public interface ISyncMessageParser {

    public Message readMessage(BufferedInputStream reader) throws IOException;

}
