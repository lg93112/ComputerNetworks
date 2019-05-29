HW2 HTTP Web Proxy: Lingsong Gao, uni: lg3018

1. Usage and port number
The usage for this program is: 
python ProxyServer.py server_ip(localhost)
The IP address of the server will be determined by server_ip in the command line, and we can use
"localhost"/"127.0.0.1" representing local host server for test.
The port number is 8080 as defined in my code.
Thus, we will use the format as follows in our browser after running the server:
http://localhost(or server_ip):8080/XXX
I'm using this url format in my browser without configuring my browser to change web proxy and simply typing http://XXX. The parse method for url is based on this "http://localhost(server_ip):8080/XXX" format without web proxy configuration in browser which will have different
request message


2. Data structure used for caching: 
loc = {} which is a dictionary of filename and last-modified-time key-value pair, which will be explained with more details in following 3 Part 3.


3. Part 1-4 and bonus parts
1) Part 1
I completed the bonus part for part 1 to better send requests from proxy to server and response from proxy to client.
i)
I used the function parse_request as explained in code notation to parse the request message by adding and modifying some request headers. Then I will send the entire modified request including all headers from proxy to server, not just GET line itself. 
For example the url typed in browser is http://localhost:8080/www.ee.columbia.edu/XXX
Then the request will be
GET /www.ee.columbia.edu/XXX HTTP/1.1
HOST: localhost: 8080
...
We now want to send the request to remote server from proxy, so we need to modify these headers as:
GET /XXX HTTP/1.1
HOST: www.ee.columbia.edu
...
Referer(if exists): http://www.ee.columbia.edu/YYY
...
If-Modified-Since(if there is a cache in our proxy): ZZZ
...
And I will send the entire request to server from proxy and make use of helpful headers.
ii) 
To send response from proxy to client, I first receive the responses from remote server in a while loop(or directly read bytes from cache) and then send the response back to client with/without caching the file simultaneously. When receiving responses from remote server using socket.recv(MAX_SIZE), this function may be blocked and it will cause our program to block a long time. Thus, I created a recv_timeout() function to receive response with time out requirements to solve this problem. And I receive the response from server or read bytes from cache with chunks specified by MAX_SIZE in a while loop, and send response to client from proxy chunks by chunks in the same loop.

2) Part 2
I add the error handling in my code by dividing codes in various try/except blocks to handle and display the error. And for the case of read and write, I add while(len(data)) to only read and write when data is not empty. And for the case of 404 NOT FOUND, I handled this response code separately in my code by directly sending the response from remote server to client without further body reading and cache file updating strategies.

3) Part 3
i) I used loc = {} which is a dictionary of filename and last-modified-time key-value pair to store file and its modified time information. As specified in code, all cached files are stored in current directory where this python resides and thus the file path is "./filename". filename is handled so that all "/" in original url path will be changed as "-" in os path. 
ii) To ensure my cached file is the most up-to-date version, I updated the last_modified_time in the loc dictionary whenever I modified the cache file in proxy. Thus, the original last_modified_time for those files with response lacking last modified date, I will set it to the GMT time of receipt originally. And I will always send conditional GET for files that have already been cached in proxy with "if-modified-since" header. If the response code is 304, it shows that this file in proxy is up-to-date, I will directly read bytes from cached file and send response back to client. Otherwise, it shows some updates exist, and I will receive response from remote server and send response back to client while updating the cached file.

4) Part 4
I completed the multi-threading bonus part by only using the main thread to accept() and make connections. Everytime a connection is made, I will create a new worker thread by using thread.start_new_thread(proxy_thread, (tcpCliSock, client_data, filename, webserver, cached)).
And for each worker thread, in the proxy_thread() function I created a new socket to connect with remote server and send/receive response and send back to clients. 
In this way, my proxy server can handle more than one requests at a time by creating new worker thread to do the real job.
And I tested the multi-thread functionality by using siege simulating 5 concurrent users each with 2 requests at a time for cs.columbia.edu:
siege http://localhost:8080/www.cs.columbia.edu -d1 -r2 -c5