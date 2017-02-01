package ch.eth.lubu.messages;

import ch.eth.lubu.connection.IMemManager;

/**
 * Created by lubu on 27.09.16.
 *
 * Format Store:
 * <command name> <key> <flags> <exptime> <bytes> [noreply]\r\n
 * get <key>\r\n
 *
 * Format Get
 */
public class Request extends HeaderMessage {

    private static final String CMD_READ = "get";
    private static final String CMD_WRITE = "set";
    private static final String CMD_DELETE = "delete";

    public Request(int conn, IMemManager manager) {
        super(conn, manager);
    }

    public int computeSize() {
        if (getHeader() == null) {
            return -1;
        }

        if(this.isRead()) {
            return headerSize;
        }

        if(isWrite()) {
            int numBytes = getNumBytes();
            return headerSize + numBytes + 2;
        }

        return -1;
    }

    public int predictFullMessageLength() {
        getHeader();
        if(header == null || header.length < 2)
            throw  new MessageException("Illegal Request Format");
        int len = 0;
        /*
        for (int i=0; i<header.length; i++)
            len += header[i].length();
        len += 1 + header.length;*/
        len += headerSize;
        len += getNumBytes() + 2;
        return len;
    }

    @Override
    public HeaderMessage createNew() {
        return new Request(-1, this.manager);
    }

    public boolean isRead() {
        getHeader();
        if(header == null || header.length < 2)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(CMD_READ);
    }

    public boolean isWrite() {
        getHeader();
        if(header == null || header.length < 2)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(CMD_WRITE);
    }

    public boolean isDelete() {
        getHeader();
        if(header == null || header.length < 2)
            throw  new MessageException("Illegal Request Format");
        return header[0].equals(CMD_DELETE);
    }

    public int getNumBytes() {
        getHeader();
        if(header == null || header.length < 4)
            throw  new MessageException("Illegal Request Format");
        return Integer.valueOf(header[4]);
    }

    @Override
    public boolean hasBody() {
        return isWrite();
    }

    public String getKey() {
        getHeader();
        if(header == null || header.length < 1)
            throw  new MessageException("Illegal Request Format");
        return header[1];
    }


}
