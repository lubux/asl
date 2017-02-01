package ch.eth.lubu.connection;

import ch.eth.lubu.util.TimeTracker;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.Closeable;
import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Created by lubu on 27.09.16.
 *
 * Implements the nio network functions for a server
 */
public class ServerConnectionProcessor implements Runnable, Closeable {

    private static Logger log = LogManager.getLogger(ServerConnectionProcessor.class.getName());

    public static final int BUFFER_SIZE = 1024 * 1024;

    private Selector inSelector    = null;
    private Selector[] outSelectors   = null;

    private IMessageFunctionsFactory msgFactory;

    private ByteBuffer rBuffer  = ByteBuffer.allocate(BUFFER_SIZE);
    private ByteBuffer[] wBuffers = null;

    private static AtomicInteger idCounter = new AtomicInteger(0);

    private IMessageProcessor messageProcessor;

    private IMemManager memManager;

    private WriteBack writeBackHandler;

    private Map<Integer, Connection> idToConnection = new ConcurrentHashMap<>();

    ServerSocketChannel serverSocketChannel = null;

    public ServerConnectionProcessor(String myip, int port, IMessageFunctionsFactory msgFactory, IMemManager memManager, int numWriters) throws IOException {
        serverSocketChannel = ServerSocketChannel.open();
        if(myip==null) {
            serverSocketChannel.socket().bind(new InetSocketAddress(port));
        } else {
            serverSocketChannel.socket().bind(new InetSocketAddress(InetAddress.getByName(myip), port));
        }

        serverSocketChannel.configureBlocking(false);

        this.msgFactory = msgFactory;

        inSelector = Selector.open();
        outSelectors = new Selector[numWriters];
        for(int i=0; i<outSelectors.length; i++)
            outSelectors[i] = Selector.open();
        wBuffers = new ByteBuffer[numWriters];
        for(int i=0; i<outSelectors.length; i++)
            wBuffers[i] =  ByteBuffer.allocate(BUFFER_SIZE);

        this.memManager = memManager;
        //Thread safe queue? 
        writeBackHandler = new WriteBack(memManager, idToConnection);

        messageProcessor = msgFactory.getProcessor();
    }



    public boolean acceptConnections() throws IOException {
        SocketChannel channel = serverSocketChannel.accept();

        if(channel != null){
            channel.configureBlocking(false);
            SelectionKey key = channel.register(inSelector, SelectionKey.OP_READ);
            IMessageParser parser = msgFactory.getParser();
            parser.setMemoryManager(memManager);
            Connection conn = new Connection(idCounter.getAndIncrement(), channel, parser, msgFactory.getWriter());
            int out_write = conn.getConnectionID() % wBuffers.length;
            channel.register(this.outSelectors[out_write % outSelectors.length], SelectionKey.OP_WRITE, conn);
            idToConnection.put(conn.getConnectionID(), conn);
            key.attach(conn);

            log.debug("Connection accepted from " + channel.getLocalAddress().toString() + " with id " + conn.getConnectionID());
            return true;
        }
        return false;
    }

    public void readFromConnections() throws IOException {
        int numConn = this.inSelector.selectNow();
        if(numConn > 0) {
            Set<SelectionKey> selectedKeys = this.inSelector.selectedKeys();
            Iterator<SelectionKey> keyIterator = selectedKeys.iterator();

            while(keyIterator.hasNext()) {
                SelectionKey key = keyIterator.next();
                Connection curConn = (Connection) key.attachment();
                curConn.getMessageParser().read(curConn, this.rBuffer);

                List<Message> arrivedMessages = curConn.getMessageParser().getMessages();
                if(arrivedMessages.size() > 0){
                    for(Message msg : arrivedMessages){
                        //add timestamp
                        msg.tracker = new TimeTracker();
                        msg.tracker.setClientRequestIn();

                        log.debug(" Start processing message from connection " + curConn.getConnectionID());
                        messageProcessor.processMessage(msg, writeBackHandler);
                    }
                    arrivedMessages.clear();
                }

                if(!curConn.isAlive()) {
                    log.debug(curConn.getConnectionID() + " has died");
                    key.cancel();
                    curConn.close();
                }

                keyIterator.remove();
            }
            selectedKeys.clear();
        }
    }

    public void writeToConnections(int id) throws IOException {
        Selector select = this.outSelectors[id % outSelectors.length];
        int numConn = select.selectNow();
        if(numConn > 0) {
            Set<SelectionKey> selectedKeys = select.selectedKeys();
            Iterator<SelectionKey> keyIterator = selectedKeys.iterator();

            while(keyIterator.hasNext()) {

                SelectionKey key = keyIterator.next();
                Connection curConn = (Connection) key.attachment();
                if(key.isValid() && key.isWritable() && curConn.getMessageWriter().hasMessages()) {
                    while(curConn.getMessageWriter().write(curConn,  wBuffers[id % wBuffers.length])) {

                    }
                }
                keyIterator.remove();
            }
            selectedKeys.clear();
        }
    }

    @Override
    public void run() {
        try {
            while(true) {
                acceptConnections();
                readFromConnections();
                writeToConnections(0);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void close() throws IOException {
        inSelector.close();
        for(int i=0; i<outSelectors.length; i++)
            outSelectors[i].close();
        serverSocketChannel.close();
    }
}
