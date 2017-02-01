package ch.eth.lubu.util;

import ch.eth.lubu.connection.IMessageSendListener;
import ch.eth.lubu.connection.Message;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.util.concurrent.atomic.AtomicLong;

/**
 * Created by lubu on 10.10.16.
 */
public class TimeLogger implements IMessageSendListener{

    private static Logger log = LogManager.getLogger("TimeLogger");
    private static final int LOGGING_INTERVALL = 100;
    private static final int LOGGING_INTERVALL_WRITE = 10;

    private static AtomicLong counterWrites = new AtomicLong(0);
    private static AtomicLong counterReads = new AtomicLong(0);

    @Override
    public void onMessageSended(Message m) {
        long curCount;
        TimeTracker tracker = m.tracker;
        tracker.setClientResponseOut();
        boolean do_log;
        if(tracker.isRead) {
            curCount = counterReads.getAndIncrement();
            do_log = curCount % LOGGING_INTERVALL == 0;
        } else {
            curCount = counterWrites.getAndIncrement();
            do_log = curCount % LOGGING_INTERVALL_WRITE == 0;
        }

        if(do_log) {
            long timeServer = tracker.serverResponseIn-tracker.serverRequestOut;
            long timeMW = (tracker.clientResponseOut-tracker.clientRequestIn) - timeServer;
            long timeMQueue = tracker.stopQueue - tracker.startQueue;
            long timeWBQueue = tracker.backQueueStop - tracker.backQueueStart;
            int success = tracker.isSuccess ? 1 : 0;
            int isRead = tracker.isRead ? 1 : 0;
            log.info(String.format("%d,%d,%d,%d,%d,%d", timeMW, timeServer, timeMQueue, timeWBQueue, isRead, success));
        }

    }

    @Override
    public void onMessageDequeued(Message m) {
        TimeTracker tracker = m.tracker;
        tracker.setBackQueueStop();
    }
}
