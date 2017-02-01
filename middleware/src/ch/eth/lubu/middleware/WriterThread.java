package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.*;
import ch.eth.lubu.connection.AsyncConnectionManager.LockedConnection;
import ch.eth.lubu.messages.MemcacheJob;
import ch.eth.lubu.messages.Response;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.SelectionKey;
import java.nio.channels.Selector;
import java.util.Arrays;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.TimeUnit;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements the writer thread in a partition
 */
public class WriterThread extends Thread {

    private static Logger log = LogManager.getLogger(WriterThread.class.getName());

    private static final int MAX_ITERS = 100000;

    public static final int BUFFER_SIZE = 1024*1024;

    private BlockingQueue<MemcacheJob> jobQueue;
    private AsyncConnectionManager manager;
    private boolean isRunning = true;
    private final int range;

    private ByteBuffer rBuffer = ByteBuffer.allocate(BUFFER_SIZE);
    private ByteBuffer wBuffer = ByteBuffer.allocate(BUFFER_SIZE);

    public WriterThread(BlockingQueue<MemcacheJob> jobQueue, AsyncConnectionManager manager, int range) {
        this.jobQueue = jobQueue;
        this.manager = manager;
        this.range = range;
    }

    public void stopWriter() {
        isRunning = false;
        this.interrupt();
    }

    private Message[] writeToDBs(MemcacheJob job, LockedConnection[] connectionsLocked) throws IOException, InterruptedException {
        Connection[] connections = new Connection[connectionsLocked.length];
        connections[0] = connectionsLocked[0].waitForConnectionBlocking();
        log.debug("Acquired lock for AsyncServerConection " + connections[0].getConnectionID());
        connections[0].getMessageWriter().enqueueMsg(job.getRequest());
        boolean[] connFWrite= new boolean[connections.length];
        boolean[] freeLock= new boolean[connections.length];
        Message[] responseMessages= new Message[connections.length];
        int lockIndex = 1;
        int sleepTime = 5;
        Arrays.fill(connFWrite, false);

        Selector inSelector = Selector.open();
        Selector outSelector = Selector.open();
        connections[0].getChannel().register(outSelector, SelectionKey.OP_WRITE);
        connections[0].getChannel().register(inSelector, SelectionKey.OP_READ);

        boolean finished = false;
        int counter = 0;
        try {
            while (!finished) {

                //try acquire locks
                for (int iter = lockIndex; iter < connections.length; iter++) {
                    connections[iter] = connectionsLocked[iter].waitForConnectionNonBlocking();
                    if (connections[iter] == null) {
                        //Lock failed
                        log.debug("Acquiring lock for AsyncServerConection " + connectionsLocked[iter].getConnectionsID() + " failed");
                        break;
                    } else {
                        log.debug("Acquired lock for AsyncServerConection " + connections[iter].getConnectionID());
                        connections[iter].getMessageWriter().enqueueMsg(job.getRequest());
                        connections[iter].getChannel().register(outSelector, SelectionKey.OP_WRITE);
                        connections[iter].getChannel().register(inSelector, SelectionKey.OP_READ);
                        lockIndex++;
                    }

                }

                //write to channels
                outSelector.selectNow();
                boolean writeFinished = true;
                for (int iter = 0; iter < connections.length; iter++) {
                    if (connections[iter] != null && !connFWrite[iter] && outSelector.selectedKeys().contains(connections[iter].getChannel().keyFor(outSelector))) {
                        IMessageWriter writer = connections[iter].getMessageWriter();
                        wBuffer.clear();
                        writer.write(connections[iter], wBuffer);
                        if (!writer.hasMessages()) {
                            connFWrite[iter] = true;
                            log.debug("Write to AsyncServerConnection " + connections[iter].getConnectionID() + " has finished");
                            connections[0].getChannel().register(inSelector, SelectionKey.OP_READ);
                        }
                    }
                    if (!connFWrite[iter])
                        writeFinished = false;
                }

                if (writeFinished && job.getRequest().tracker.serverRequestOut==-1) {
                    //set timestamp if all request to replicas send
                    job.getRequest().tracker.setServerRequestOut();
                }


                inSelector.selectNow();
                //read from channels
                for (int iter = 0; iter < connections.length; iter++) {
                    if (connections[iter] != null && connFWrite[iter] && (responseMessages[iter] == null) && inSelector.selectedKeys().contains(connections[iter].getChannel().keyFor(inSelector))) {
                        IMessageParser parser = connections[iter].getMessageParser();
                        log.debug("read");
                        parser.read(connections[iter], rBuffer);
                        if (!parser.getMessages().isEmpty()) {
                            responseMessages[iter] = parser.getMessages().get(0);
                            parser.getMessages().clear();
                            log.debug("Response from AsyncServerConnection " + connections[iter].getConnectionID() + " received");
                        }
                    }
                }

                //release finished Task locks
                for (int iter = 0; iter < connections.length; iter++) {
                    if (connections[iter] != null && connFWrite[iter] && (responseMessages[iter] != null)) {
                        if (!freeLock[iter]) {
                            connectionsLocked[iter].release();
                            freeLock[iter] = true;
                            log.debug("AsyncServerConnection " + connections[iter].getConnectionID() + " has been released");
                        }
                    }
                }

                finished = true;
                for (int iter = 0; iter < connections.length; iter++) {
                    if (connections[iter] == null || !connFWrite[iter] || (responseMessages[iter] == null)) {
                        finished = false;
                        break;
                    }
                }

                if (finished) {
                    //set timestamp for all resposnes received
                    job.getRequest().tracker.setServerResponseIn();
                }

                if (++counter >= MAX_ITERS) {
                    //throw new MWException("JOB failed max iters reached " + new String(job.getRequest().getAsByteArray()));
                }
                if (counter % 100 == 0) {
                    //Thread.sleep(sleepTime);
                }

            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            inSelector.close();
            outSelector.close();
        }
        return responseMessages;
    }

    private void processJob(MemcacheJob job) throws IOException, InterruptedException {
        LockedConnection[] connectionsLocked = manager.aquireRange(job.getPartitionID(), range);
        if(connectionsLocked.length<1)
            return;

        log.debug("Start processing write job at partition " + job.getPartitionID());

        Message[] msgs = writeToDBs(job, connectionsLocked);
        int indx = 0;
        for(Message msg : msgs) {
            if(!(msg instanceof Response)) {
                throw new MWException("Illegal Message received! Should be response");
            }
            Response response = (Response) msg;
            if(!(response.isSuccessStored() || response.isSuccessDelete())) {
                break;
            }
            indx++;
        }

        if(indx<connectionsLocked.length) {
            msgs[indx].setConnID(job.getRequest().getConn());
            msgs[indx].tracker = job.getRequest().tracker;
            job.getBack().enqueueMessage(msgs[indx]);
            msgs[indx].tracker.isSuccess = false;
            log.debug("Write Job failed for serverid " + indx);
        } else {
            msgs[0].setConnID(job.getRequest().getConn());
            msgs[0].tracker = job.getRequest().tracker;
            job.getBack().enqueueMessage(msgs[0]);
            msgs[0].tracker.isSuccess = true;
            log.debug("Successful write Job");
        }

    }

    @Override
    public void run() {
        while (isRunning) {
            MemcacheJob job = null;
            try {
                job = jobQueue.take();
                log.debug("Writer took one request");
                job.getRequest().tracker.setStopQueue();
                processJob(job);
            } catch (Exception e) {
                if(!(e instanceof InterruptedException))
                    if(job!=null) {
                        Message m = job.getRequest().createNew();
                        m.writeData("ERROR\t\n".getBytes());
                        m.tracker = job.getRequest().tracker;
                        m.setConnID(job.getRequest().getConn());
                        job.getBack().enqueueMessage(m);
                    }
            } finally {
                if(job!=null) {
                    job.getRequest().close();
                }
            }
        }
    }
}
