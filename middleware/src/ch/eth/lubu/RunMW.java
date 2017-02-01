package ch.eth.lubu;

import ch.eth.lubu.messages.IPartitionFunction;
import ch.eth.lubu.middleware.Middleware;
import ch.eth.lubu.util.DumbMemoryManager;
import ch.eth.lubu.util.IntervalCRC32Hasher;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.Semaphore;

public class RunMW {

	static String myIp = null;
	static int myPort = 0;
	static List<String> mcAddresses = null;
	static int numThreadsPTP = -1;
	static int writeToCount = -1;

	//optional args
	static int experimentID = -1;
	static int duration = -1;
	static int numBackwriters = -1;

	private static final int DURATION_EXPERIMENT = 1;

	public static void main(String[] args) throws Exception {

		// -----------------------------------------------------------------------------
		// Parse and prepare arguments
		// -----------------------------------------------------------------------------

		parseArguments(args);

		// -----------------------------------------------------------------------------
		// Start the Middleware
		// -----------------------------------------------------------------------------

		Middleware m = null;
		String[] ips = new String[mcAddresses.size()];
		int[] ports = new int[mcAddresses.size()];

		int count=0;
		for(String mcAddress : mcAddresses) {
			mcAddress = mcAddress.replace(" ", "");
			String[] split = mcAddress.split(":");

			if(split.length != 2) {
				System.err.println("Illegal memcached backend server IP " + mcAddress);
				System.exit(1);
			}

			ips[count] = split[0];
			ports[count] = Integer.valueOf(split[1]);
			count++;
		}

		try {
			DumbMemoryManager ma = new DumbMemoryManager(1024 * 2);
			IPartitionFunction func = new IntervalCRC32Hasher();
			if(numBackwriters==-1)
				numBackwriters = 2; //default 2 backwriter threads
			m = new Middleware(myIp, myPort, ips, ports, numThreadsPTP, numThreadsPTP, writeToCount, ips.length, numBackwriters, ma, func);
			m.start();

		} catch (IOException e) {
			e.printStackTrace();
		}
		if (m != null)
			if(experimentID==DURATION_EXPERIMENT && duration>0) {
				Thread.sleep(duration * 1000);
				m.stop();
			} else {
				Semaphore sem = new Semaphore(0);
				try {
					sem.acquire();
				} catch (InterruptedException i) {
					m.stop();
				}
			}
	}

	private static void parseArguments(String[] args) {
		Map<String, List<String>> params = new HashMap<>();

		List<String> options = null;
		for (int i = 0; i < args.length; i++) {
			final String a = args[i];

			if (a.charAt(0) == '-') {
				if (a.length() < 2) {
					System.err.println("Error at argument " + a);
					System.exit(1);
				}

				options = new ArrayList<String>();
				params.put(a.substring(1), options);
			} else if (options != null) {
				options.add(a);
			} else {
				System.err.println("Illegal parameter usage");
				System.exit(1);
			}
		}

		if (params.size() == 0) {
			printUsageWithError(null);
			System.exit(1);
		}

		if (params.get("l") != null)
			myIp = params.get("l").get(0);
		else {
			printUsageWithError("Provide this machine's external IP! (see ifconfig or your VM setup)");
			System.exit(1);			
		}

		if (params.get("p") != null)
			myPort = Integer.parseInt(params.get("p").get(0));
		else {
			printUsageWithError("Provide the port, that the middleware listens to (e.g. 11212)!");
			System.exit(1);			
		}

		if (params.get("m") != null) {
			mcAddresses = params.get("m");
		} else {
			printUsageWithError(
					"Give at least one memcached backend server IP address and port (e.g. 123.11.11.10:11211)!");
			System.exit(1);
		}

		if (params.get("t") != null)
			numThreadsPTP = Integer.parseInt(params.get("t").get(0));
		else {
			printUsageWithError("Provide the number of threads for the threadpool for each server (e.g. 4)!");
			System.exit(1);
		}

		if (params.get("r") != null)
			writeToCount = Integer.parseInt(params.get("r").get(0));
		else {
			printUsageWithError("Provide the replication factor (1=not replicated)!");
			System.exit(1);
		}

		if (params.get("e") != null)
			experimentID = Integer.parseInt(params.get("e").get(0));

		if (params.get("d") != null)
			duration = Integer.parseInt(params.get("d").get(0));

		if (params.get("k") != null)
			numBackwriters = Integer.parseInt(params.get("k").get(0));


	}

	private static void printUsageWithError(String errorMessage) {
		System.err.println();
		System.err.println(
				"Usage: -l <MyIP> -p <MyListenPort> -t <NumberOfThreadsInPools> -r <WriteToThisManyServers> -m <MemcachedIP:Port> <MemcachedIP2:Port2> ...");
		if (errorMessage != null) {
			System.err.println();
			System.err.println("Error message: " + errorMessage);
		}

	}
}
