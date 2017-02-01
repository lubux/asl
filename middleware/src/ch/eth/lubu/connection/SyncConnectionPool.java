package ch.eth.lubu.connection;

import java.io.Closeable;
import java.io.IOException;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements a thread safe synchronus connection pool
 *
 */
public class SyncConnectionPool implements Closeable {

    private SyncConnection[] connections;
    private BlockingQueue<SyncConnection> freeConnections;

    public SyncConnectionPool(int numConnections, ISyncMessageParser messageParser, String ip, int port) throws IOException {
        connections = new SyncConnection[numConnections];
        freeConnections = new ArrayBlockingQueue<>(numConnections);
        for (int id=0; id < numConnections; id++) {
            connections[id] = new SyncConnection(id, messageParser, ip, port);
            freeConnections.add(connections[id]);
        }
    }

    public SyncConnection getConnection() throws InterruptedException {
        return freeConnections.take();
    }

    /**
     * Should be only called ONCE per connection
     * @param conn
     * @throws InterruptedException
     */
    public void releaseConnection(SyncConnection conn) throws InterruptedException {
        freeConnections.put(conn);
    }

    @Override
    public void close() throws IOException {
        for(SyncConnection conn: connections)
            conn.close();
    }
}
