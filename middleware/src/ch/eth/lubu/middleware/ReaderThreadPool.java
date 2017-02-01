package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.Message;
import ch.eth.lubu.connection.ServerConnectionProcessor;
import ch.eth.lubu.connection.SyncConnection;
import ch.eth.lubu.connection.SyncConnectionPool;
import ch.eth.lubu.messages.MemcacheJob;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.util.concurrent.BlockingQueue;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements the reader thread pool in a partition
 */
public class ReaderThreadPool {

    private static Logger log = LogManager.getLogger(ServerConnectionProcessor.class.getName());

    private SyncConnectionPool connectionPool;
    private BlockingQueue<MemcacheJob> jobQueue;
    private ReaderThread[] threads;

    public ReaderThreadPool(int numThreads, SyncConnectionPool connectionPool, BlockingQueue<MemcacheJob> jobQueue) {
        this.connectionPool = connectionPool;
        this.jobQueue = jobQueue;
        threads = new ReaderThread[numThreads];
        for(int iter=0; iter<numThreads; iter++) {
            threads[iter] = new ReaderThread();
        }
    }

    public void startThreads() {
        for(ReaderThread thread : threads)
            thread.start();
    }

    public void stopThreads() {
        for(ReaderThread thread : threads)
            thread.stopReaderThread();
    }

    private class ReaderThread extends Thread {

        private boolean running = true;

        public ReaderThread() {
        }

        public void stopReaderThread() {
            running = false;
            this.interrupt();
        }

        private void process(MemcacheJob job) throws InterruptedException {
            SyncConnection conn = null;
            log.debug("Process Read Job at Partition " + job.getPartitionID());
            try {
                conn = connectionPool.getConnection();
                log.debug("SyncConnection acquired with id " + conn.getConnectionID());
                conn.writeMessage(job.getRequest());
                job.getRequest().tracker.setServerRequestOut();
                Message response = conn.readMessage();
                response.setConnID(job.getRequest().getConn());
                response.tracker = job.getRequest().tracker;
                response.tracker.setServerResponseIn();
                job.getBack().enqueueMessage(response);
                log.debug("Enqueued response bach to client witd connID " + response.getConn());
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
                if(conn!=null) {
                    connectionPool.releaseConnection(conn);
                    log.debug("SyncConnection released with id " + conn.getConnectionID());
                }
            }
        }

        @Override
        public void run() {
            super.run();
            while (running) {
                MemcacheJob job = null;
                try {
                    job = jobQueue.take();
                    log.debug("Reader took one Request");
                    job.getRequest().tracker.setStopQueue();
                    process(job);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                } finally {
                    if(job!=null)
                        job.getRequest().close();
                }
            }
        }
    }

}
