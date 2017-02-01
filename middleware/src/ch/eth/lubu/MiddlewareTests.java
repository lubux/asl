package ch.eth.lubu;

import ch.eth.lubu.connection.IMemManager;
import ch.eth.lubu.messages.IPartitionFunction;
import ch.eth.lubu.middleware.Middleware;
import ch.eth.lubu.util.*;
import junit.framework.TestCase;
import org.junit.Test;

import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.Socket;
import java.util.Arrays;
import java.util.Random;
import java.util.concurrent.Semaphore;

/**
 * Created by lubu on 01.10.16.
 */
public class MiddlewareTests extends TestCase {

    private static char[] chars = "abcdefghijklmnopqrstuvwxyz".toCharArray();
    private static int id=0;
    private static Random random = new Random();

    public static String generateRandomString(int len) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < len; i++) {
            char c = chars[random.nextInt(chars.length)];
            sb.append(c);
        }
        return sb.toString();
    }

    public static String generateWriteCMD(int len, String key) {
        StringBuilder sb = new StringBuilder();
        sb.append("set ").append(key).append(" 0 900 ").append(len).append("\r\n");
        sb.append(generateRandomString(len));
        sb.append("\r\n");
        return sb.toString();
    }

    private static String generateReadCMD(String key) {
        StringBuilder sb = new StringBuilder();
        sb.append("get ").append(key);
        sb.append("\r\n");
        return sb.toString();
    }

    private static String generateDeleteCMD(String key) {
        StringBuilder sb = new StringBuilder();
        sb.append("delete ").append(key);
        sb.append("\r\n");
        return sb.toString();
    }

    private static void startMiddelWareTest(int numPartitions, int numClientThreads, IMemManager ma, IPartitionFunction func, int numIter) {
        int localPort = 11400;
        String[] ips = new String[numPartitions];
        Process[] processes = new Process[numPartitions];
        ClientThread[] threads = new ClientThread[numClientThreads];
        Semaphore sem = new Semaphore(-numClientThreads + 1);
        int[] ports = new int[numPartitions];
        Arrays.fill(ips, "localhost");
        for(int i=1; i<=numPartitions;i++) {
            ports[i-1]=localPort+i;
        }

        for(int i=0; i<numPartitions;i++) {
            Runtime rt = Runtime.getRuntime();
            try {
                processes[i] = rt.exec("memcached -p "+ports[i]+" -t 1");
            } catch (IOException e) {
                e.printStackTrace();
            }
        }

        Middleware m = null;
        try {
            m = new Middleware(null, localPort, ips, ports, 4, 4, 2, 3, 1, ma, func);
            m.start();
            for(int i=0; i<numClientThreads;i++) {
                threads[i] = new ClientThread(i, localPort, numIter, sem);
                threads[i].start();
            }


            sem.acquire();

            for(int i=0; i<numClientThreads;i++) {
                assertTrue(threads[i].success && threads[i].finished);
            }

        } catch (IOException e) {
            e.printStackTrace();
        } catch (InterruptedException e) {
            e.printStackTrace();
        } finally {
            m.stop();

            for(int i=0; i<numPartitions;i++) {
                if(processes[i]!=null)
                    processes[i].destroy();
            }
        }


    }

    @Test
    public void testdebugMW() {
        Middleware m = null;
        Semaphore sem = new Semaphore(0);
        try {
            DumbMemoryManager ma = new DumbMemoryManager(1024 * 2);
            IPartitionFunction func = new IntervalCRC32Hasher();
            m = new Middleware("localhost", 11500, new String[] {"localhost", "localhost"}, new int[] {11501, 11502}, 2, 2, 2, 2, 16,ma, func);
            m.start();

        } catch (IOException e) {
            e.printStackTrace();
        }

        try {
            sem.acquire();
        } catch (InterruptedException e) {
            if(m!=null)
                m.stop();
        }

    }

    @Test
    public void testMemcache() {
        DumbMemoryManager ma = new DumbMemoryManager(100);
        IPartitionFunction func = new IntervalCRC32Hasher();
        //startMiddelWareTest(4,100, ma, func, 1000);
        startMiddelWareTest(4,100, ma, func, 1000);
    }

    public static class ClientThread extends Thread {

        private int id;
        private int port;
        private int iter;

        private Semaphore sem;

        boolean success = true;
        boolean finished = false;

        public ClientThread(int id, int port, int iter, Semaphore sem) {
            this.id = id;
            this.port = port;
            this.iter = iter;
            this.sem = sem;
        }

        @Override
        public void run() {
            super.run();
            Socket clientSocket = null;
            DataOutputStream outToServer = null;
            BufferedReader inFromServer = null;
            try {
                clientSocket = new Socket("localhost", port);
                inFromServer = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));
                outToServer = new DataOutputStream(clientSocket.getOutputStream());

                for(int i=0; i<iter; i++){
                    String key = "t" +id+"k"+i;
                    String write = generateWriteCMD(200,key);
                    //String write = generateWriteCMD(20, String.valueOf(i));
                    outToServer.writeBytes(write);
                    outToServer.flush();
                    String response = inFromServer.readLine();
                    System.out.println("T"+id+" Response Store: " + response);

                    String readCMD =generateReadCMD(key);
                    outToServer.writeBytes(readCMD);
                    outToServer.flush();
                    response = inFromServer.readLine();
                    if(!response.contains("VALUE")) {
                        System.out.println("T"+id+" Response Read: " + response);
                        success = false;
                    } else {
                        String data = inFromServer.readLine();
                        inFromServer.readLine();
                        System.out.println("T"+id+" Response Read: " + response + " -> " + data);
                        if(!write.contains(data))
                            success = false;
                    }


                    outToServer.writeBytes(generateDeleteCMD(key));
                    outToServer.flush();
                    response = inFromServer.readLine();
                    System.out.println("T"+id+" Response Delete: " + response);
                    if(!response.contains("DELETED"))
                        success = false;
                }
                finished = true;

            } catch (IOException e) {
                e.printStackTrace();
            } finally {
                    try {
                        if(clientSocket!=null)
                            clientSocket.close();
                        if(outToServer!=null)
                            outToServer.close();
                        if(inFromServer!=null)
                            inFromServer.close();
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                    sem.release();

            }

        }
    }

}
