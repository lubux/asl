package ch.eth.lubu.connection;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.nio.channels.SocketChannel;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements a thread safe asynchron connection pool
 * User for writer thread
 *
 */
public class AsyncConnectionManager {

    private LockedConnection[] connections;

    public AsyncConnectionManager(String[] ips, int[] ports, IMessageFunctionsFactory factory, IMemManager manager) throws IOException {
        connections = new LockedConnection[ips.length];
        for (int id=0; id<ips.length; id++) {
            SocketChannel socketChannel = SocketChannel.open();
            socketChannel.connect(new InetSocketAddress(ips[id], ports[id]));
            socketChannel.configureBlocking(false);
            IMessageParser parser = factory.getParser();
            parser.setMemoryManager(manager);
            connections[id] = new LockedConnection(new Connection(id, socketChannel, parser, factory.getWriter()));
        }
    }

    public LockedConnection[] aquireRange(int connectionID, int range) {
        LockedConnection[] res = new LockedConnection[range];
        if(connectionID + range > connections.length) {
            int tempLen = connections.length - connectionID;
            System.arraycopy(connections, 0, res , 0,  range-tempLen);
            System.arraycopy(connections, connectionID, res, range-tempLen,  tempLen);

        } else {
            System.arraycopy(connections, connectionID, res, 0, range);
        }
        return res;
    }

    public static class LockedConnection {

        private Connection connection;
        private ReentrantLock lock;

        public LockedConnection(Connection connection) {
            this.connection = connection;
            lock = new ReentrantLock(true);
        }

        public Connection waitForConnectionBlocking() {
            lock.lock();
            return connection;
        }

        public Connection waitForConnectionNonBlocking() {
            boolean success = false;
            try {
                success = lock.tryLock(1, TimeUnit.MILLISECONDS);
            } catch (InterruptedException e) {
                return null;
            }
            if(success)
                return connection;
            else
                return null;
        }

        public void release() {
            if(!lock.isHeldByCurrentThread())
                throw new RuntimeException("Illegal locking state");
            lock.unlock();
        }

        public int getConnectionsID() {
            return this.connection.getConnectionID();
        }
    }


}
