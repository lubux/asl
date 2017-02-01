package ch.eth.lubu.messages;

import ch.eth.lubu.connection.IMemManager;

/**
 * Created by lubu on 27.09.16.
 *
 * no content response: STORED\r\n
 *
 * content response:
 * VALUE <key> <flags> <bytes> [<cas unique>]\r\n
 * <data block>\r\n
 * END\r\n
 */
public class Response extends HeaderMessage {

    private static final String OK_DELETE = "DELETED";
    private static final String OK_READ = "VALUE";
    private static final String OK_STORE = "STORED";

    public Response(int conn, IMemManager manager) {
        super(conn, manager);
    }

    public boolean isSuccessStored() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(OK_STORE);
    }

    public boolean isSuccessDelete() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(OK_DELETE);
    }

    public boolean isSuccessRead() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(OK_READ);
    }

    public int getNumBytesRead() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        return Integer.valueOf(header[3]);
    }

    @Override
    public int predictFullMessageLength() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        int len = 0;
        for (String token : header)
            len += token.length();
        len += 1 + header.length;
        len += getNumBytesRead() + 7;
        return len;
    }

    @Override
    public HeaderMessage createNew() {
        return new Response(-1, this.manager);
    }

    @Override
    public boolean hasBody() {
        return isSuccessRead();
    }

}
