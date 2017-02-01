package ch.eth.lubu;

import ch.eth.lubu.connection.Message;
import ch.eth.lubu.connection.ServerConnectionProcessor;
import ch.eth.lubu.messages.*;
import ch.eth.lubu.util.IntervalCRC32Hasher;
import ch.eth.lubu.util.DumbMemoryManager;
import junit.framework.TestCase;

import java.io.*;
import java.net.Socket;
import java.nio.ByteBuffer;

/**
 * Created by lubu on 28.09.16.
 */
public class BasicTests extends TestCase {


    @org.junit.Test
    public void testMessage2() {
        DumbMemoryManager ma = new DumbMemoryManager(3);
        Message m = new Message(1, ma);
        byte[] test = new byte[10];
        for(int i=0; i<test.length; i++) {
            test[i] = 1;
        }
        ByteBuffer buff = ByteBuffer.wrap(test);
        m.writeData(buff);
        buff = ByteBuffer.wrap(test);
        m.writeData(buff);

        assertEquals(test.length*2, m.getLen());


        buff = ByteBuffer.wrap(test);
        m.writeData(buff, 2);

        assertEquals(test.length*2 + 2, m.getLen());
    }

    @org.junit.Test
    public void testMessage3() {
        DumbMemoryManager ma = new DumbMemoryManager(100);
        Request m = new Request(1, ma);
        String read = "get sdfsfhsdkfjfsd\r\n";
        ByteBuffer buff = ByteBuffer.wrap(read.getBytes());
        m.writeData(buff);

        assertTrue(m.isRead());

        m = new Request(1, ma);
        String write = "put mykey 0 0 5 noreply\r\nabcde\r\n";
        buff = ByteBuffer.wrap(write.getBytes());
        m.writeData(buff);

        assertTrue(m.isWrite());
        assertTrue(m.getNumBytes() == 5);
        assertTrue(m.getKey().equals("mykey"));
    }

    @org.junit.Test
    public void testMessage5() {
        DumbMemoryManager ma = new DumbMemoryManager(500);
        byte[] test = new byte[]{115, 101, 116, 32, -48, -112, 59, 16, 16, 16, 16, 16, 49, 56, 57, 70, 114, 66, 87, 57, 32, 48, 32, 48, 32, 49, 50, 56, 13, 10};
        Request m = new Request(1, ma);
        ByteBuffer buff = ByteBuffer.wrap(test);
        m.writeData(buff);

        m.hasBody();
        int len = m.predictFullMessageLength();
        String key = m.getKey();
        byte[] bytes = key.getBytes();


        assertTrue(m.isWrite() && m.hasBody());
        assertTrue(len == test.length + 128 + 2);
    }

    @org.junit.Test
    public void testMBasicSyncParse() {
        /*
        DumbMemoryManager ma = new DumbMemoryManager(100);
        String write = "put mykey 0 0 5 noreply\r\nabcde\r\n";
        HeaderMessageParser parser = new HeaderMessageParser(true);
        parser.setMemoryManager(ma);
        try {
            Message message = parser.readMessage(new BufferedReader(new InputStream(write)));
            String res = new String(message.getAsByteArray());
            assertEquals(write, res);
        } catch (IOException e) {
            e.printStackTrace();
        }*/

    }

    @org.junit.Test
    public void testConnection() {
        try {
            ServerConnectionProcessor proc = new ServerConnectionProcessor(null, 12345, new MProcFactory(), new DumbMemoryManager(100), 1);
            Thread t = new Thread(proc);
            t.start();
            String write = "put mykey 0 0 5 noreply\r\nabcde\r\n";
            //String read = "get sdfsfhsdkfjfsd\r\n";
            Socket clientSocket = new Socket("localhost", 12345);
            DataOutputStream outToServer = new DataOutputStream(clientSocket.getOutputStream());
            BufferedReader inFromServer = new BufferedReader(new InputStreamReader(clientSocket.getInputStream()));

            outToServer.writeBytes(write);
            String response = inFromServer.readLine();
            System.out.println("Response: " + response);
            assertEquals(response, "Hello:)");

            Thread.sleep(1000);
            t.stop();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (InterruptedException e) {
            e.printStackTrace();
        }


    }

    @org.junit.Test
    public void testNone() {
        String test = "STORED\r\n";
        test = test.replace("\r\n", "");
        String[] split = test.split(" ");
        int i = 0;
    }

    @org.junit.Test
    public void testCRC32Hasher() {
        int count_0 = 0, count_1 = 0;
        for(int i=0; i<100000;i++) {
            String test = MiddlewareTests.generateRandomString(16);
            IntervalCRC32Hasher hasher = new IntervalCRC32Hasher();
            int res = hasher.hashToPartition(2, test);
            if (res == 0)
                count_0++;
            else
                count_1++;
            assertTrue(res==0 || res==1);
        }

        System.out.println("Count0: "+count_0 + " Count1: " + count_1);
    }

    @org.junit.Test
    public void runWare() {
        DumbMemoryManager ma = new DumbMemoryManager(3);
        Message m = new Message(1, ma);
        byte[] test = new byte[10];
        for(int i=0; i<test.length; i++) {
            test[i] = 1;
        }
        m.writeData(test);
        m.writeData(test);

        assertEquals(test.length*2, m.getLen());

    }






}
