package ch.eth.lubu.connection;

import java.util.Map;
import java.util.Queue;

/**
 * Created by lubu on 28.09.16.
 */
public class WriteBack {

    private IMemManager memManager;

    private Map<Integer, Connection> idToConnection;

    public WriteBack(IMemManager memManager, Map<Integer, Connection> idToConnection) {
        this.memManager = memManager;
        this.idToConnection = idToConnection;
    }

    public Message getEmptyMessage(int id) {
        return new Message(id, memManager);
    }

    public void enqueueMessage(Message m) {
        m.tracker.setBackQueueStart();
        Connection conn = idToConnection.get(m.getConn());
        conn.getMessageWriter().enqueueMsg(m);
    }

}
