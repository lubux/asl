package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.AsyncConnectionManager;
import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.connection.ServerConnectionProcessor;
import ch.eth.lubu.connection.SyncConnectionPool;
import ch.eth.lubu.messages.HeaderMessageParser;
import ch.eth.lubu.messages.IPartition;
import ch.eth.lubu.messages.MemcacheJob;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * Created by lubu on 29.09.16.
 *
 * Implements a Partition in the middleware
 *
 */
public class ProcessingPartition implements IPartition {

    private static Logger log = LogManager.getLogger(ServerConnectionProcessor.class.getName());

    public final static int QUEUE_SIZE = 1000;

    private int id;
    private BlockingQueue<MemcacheJob> writeJobQueue = new LinkedBlockingQueue<>();
    private BlockingQueue<MemcacheJob> readJobQueue = new LinkedBlockingQueue<>();

    private WriterThread writer;
    private ReaderThreadPool readerPool;

    private AsyncConnectionManager asyncConnectionManager;
    private SyncConnectionPool syncConnectionPool;

    public ProcessingPartition(int id,
                               String ip, int port,
                               AsyncConnectionManager asyncConnectionManager,
                               int numConnections, int numReaderThreads, int rangeWrite,
                               IMemManager manager) throws IOException {
        this.id = id;
        this.asyncConnectionManager = asyncConnectionManager;
        HeaderMessageParser parser = new HeaderMessageParser(false);
        parser.setMemoryManager(manager);
        this.syncConnectionPool = new SyncConnectionPool(numConnections, parser, ip, port);

        this.writer = new WriterThread(writeJobQueue, asyncConnectionManager, rangeWrite);
        this.readerPool = new ReaderThreadPool(numReaderThreads, syncConnectionPool, readJobQueue);
    }

    public void start() {
        writer.start();
        readerPool.startThreads();
    }

    public void stop() {
        writer.stopWriter();
        readerPool.stopThreads();
    }

    @Override
    public int getID() {
        return id;
    }

    @Override
    public void putWriteQueue(MemcacheJob job) {
        log.debug("Put job to Write Queue " + job.getRequest().getConn());
        job.getRequest().tracker.setStartQueue();
        job.getRequest().tracker.isRead = false;
        try {
            writeJobQueue.put(job);
        } catch (InterruptedException e) {
            e.printStackTrace();


        }
    }

    @Override
    public void putReadQueue(MemcacheJob job) {
        log.debug("Put job to Read Queue " + job.getRequest().getConn());
        job.getRequest().tracker.setStartQueue();
        job.getRequest().tracker.isRead = true;
        try {
            readJobQueue.put(job);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
    }
}
