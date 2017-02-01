package ch.eth.lubu.util;

/**
 * Created by lubu on 10.10.16.
 */
public class TimeTracker {

    public long clientRequestIn = -1;
    public long clientResponseOut = -1;
    public long serverRequestOut = -1;
    public long serverResponseIn = -1;
    public long startQueue = -1;
    public long stopQueue = -1;
    public long backQueueStart = -1;
    public long backQueueStop = -1;

    public boolean isRead = true;
    public boolean isSuccess = true;

    public void setRead(boolean read) {
        isRead = read;
    }

    public void setClientRequestIn() {
        this.clientRequestIn = getTime();
    }

    public void setClientResponseOut() {
        this.clientResponseOut = getTime();
    }

    public void setServerRequestOut() {
        this.serverRequestOut = getTime();
    }

    public void setServerResponseIn() {
        this.serverResponseIn = getTime();
    }

    public void setStartQueue() {
        this.startQueue = getTime();
    }

    public void setStopQueue() {
        this.stopQueue = getTime();
    }

    public void setBackQueueStart() {
        this.backQueueStart = getTime();
    }

    public void setBackQueueStop() {
        this.backQueueStop = getTime();
    }

    private static long getTime() {
        return System.nanoTime();
    }


}


