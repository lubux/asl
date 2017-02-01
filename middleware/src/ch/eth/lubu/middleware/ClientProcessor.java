package ch.eth.lubu.middleware;

import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.connection.IMessageFunctionsFactory;
import ch.eth.lubu.connection.ServerConnectionProcessor;

import java.io.IOException;

/**
 * Created by lubu on 29.09.16.
 * Implements the client interface for incoming request
 */
public class ClientProcessor {

    private ServerConnectionProcessor processor;
    private ReaderThread readerThread;
    private WriterThread[] writerThreads;

    private boolean running = true;

    public ClientProcessor(String myip, int port, IMessageFunctionsFactory msgFactory, IMemManager memManager, int numWriters) throws IOException {
        processor = new ServerConnectionProcessor(myip, port, msgFactory, memManager, numWriters);
        readerThread = new ReaderThread();
        writerThreads = new WriterThread[numWriters];
        for(int i=0;i<writerThreads.length; i++) {
            writerThreads[i] = new WriterThread(i);
        }
    }

    public void start() {
        readerThread.start();
        for(int i=0;i<writerThreads.length; i++) {
            writerThreads[i].start();
        }
    }

    public void stop() {
        running = false;
    }

    private class ReaderThread extends Thread {
        @Override
        public void run() {
            super.run();
            while (running) {
                try {
                    processor.acceptConnections();
                    processor.readFromConnections();
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }

    private class WriterThread extends Thread {

        int id;

        public WriterThread(int id) {
            this.id = id;
        }

        @Override
        public void run() {
            super.run();
            while (running) {
                try {
                    processor.writeToConnections(id);
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }
        }
    }

}
