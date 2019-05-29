from socket import *
import sys
import thread
import os
from datetime import datetime
import time
import threading

# global variables
MAX_CONNECTION = 16
BUFFER_SIZE = 4096
CACHE_DIR = "./"
log = {}

if len(sys.argv) <= 1:
	print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
	sys.exit(2)

# Get the serverIP from command line
try:
	serverIP = sys.argv[1]
except:
	print "serverIP error"
	sys.exit(2)

# update/add file log for their last modified dates
def update_log(filename):
	curr_time = time.strftime("%a, %d %b %Y %I:%M:%S GMT", time.gmtime())
	log[filename] = curr_time

# get file last modified date and cache path which is "./filename"
def get_log(filename):
	if filename in log:
		return CACHE_DIR+filename, log[filename]
	else:
		return CACHE_DIR+filename, None

# Get referer header line index in request and remove localhost:8080 in referer header
# eg: Referer: http://localhost:8080/www.ee.columbia.edu/ -> Referer: http://www.ee.columbia.edu/
# return referer header line index in request, -1 if there is no referer header
def get_referer(lines):
	for i in range(len(lines)):
		line_split = lines[i].split(' ')
		if(line_split[0] == "Referer:"):
			url = line_split[1]
			local = url.find("://")+3
			temp = url[local:]
			web = temp.find("/")+1
			lines[i] = "Referer: %s" % (url[:local]+temp[web:]) 
			return i
	return -1

# Add/Modify if-modified-since header for conditional GET if there is a cache in our proxy 
# If there is a cache, last_modified of the file is not None
def update_if_modified(lines, last_modified):
	if lines[len(lines)-1].split()[0] != 'If-Modified-Since:': 
		lines.append("If-Modified-Since: %s" % last_modified)
	else:
		lines[len(lines)-1] = "If-Modified-Since: %s" % last_modified

# parse request message
def parse_request(message, host):
	'''
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
	'''
	# parse the first line, eg: GET /www.ee.columbia.edu/XXX HTTP/1.1
	lines = message.splitlines()
	while lines[len(lines)-1] == '':
		lines.remove('')
	first_line = lines[0]
	first_line_split = first_line.split(' ')

	# get url excluding '/' eg: www.ee.columbia.edu/XXX
	url = first_line_split[1]

	# find the webserver eg: www.ee.columbia.edu
	temp = url[1:]
	webserver_pos = temp.find("/")
	if webserver_pos == -1:
		webserver_pos = len(temp)
		first_line_split[1] = "/" #eg: GET /www.ee.columbia.edu HTTP/1.1 -> GET / HTTP/1.1
	else:
		first_line_split[1] = temp[webserver_pos:] #eg: GET /www.ee.columbia.edu/XXX -> GET /XXX HTTP/1.1
	webserver = ""
	webserver = temp[:webserver_pos]

	# filename to store in our proxy if it needs to be cached
	filename = ''.join('-' if l == '/' else l for l in temp)

	# generate client data to be sent to remote server from proxy
	ref = get_referer(lines)
	# cache indicates if this is our requested file which needs to be cached, or simply a refered file with no need to cache
	cached = True 
	if ref != -1: # refered file
		webserver = host
		l = lines[0].split(' ')
		line_f = l[1].split("/")
		if line_f[1] == host:
			l[1] = "/" + "/".join(line_f[2:])
			lines[0] = " ".join(l)
		cached = False
	else: 
		lines[0] = ' '.join(first_line_split)
	# modify host from Host: localhost/8080(proxy) to Host: www.ee.columbia.edu(remote server)
	lines[1] = "Host: %s" % webserver
	# Get last modified date if there is such file
	cache_path, last_modified = get_log(filename)
	# Update if-modified-since header
	if last_modified:
		update_if_modified(lines, last_modified)
	# Form the client request to send from proxy to server
	client_data = "\r\n".join(lines) + '\r\n\r\n'

	print "filename if to be cached:", filename
	print "Request:"
	print client_data

	return webserver, filename, client_data, cached


# main for tcpSerSock to accept
def main():
	try:
		# Create a server socket, bind it to a port and start listening
		tcpSerSock = socket(AF_INET, SOCK_STREAM)
		# Fill in start.
		serverPort = 8080
		tcpSerSock.bind((serverIP, serverPort))
		tcpSerSock.listen(MAX_CONNECTION)
		host = None
		# Fill in end.
	except Exception as e:
		print ("Error in starting the proxy server: %s" % e)
		tcpSerSock.close()
		sys.exit(2)

	# Always-on server loop to accept connections
	while 1:
		try:
			# Start receiving data from the client
			print('Ready to serve...')
			tcpCliSock, addr = tcpSerSock.accept()
			print('Received a connection from:', addr)
			message = tcpCliSock.recv(BUFFER_SIZE) # Fill in start. # Fill in end.
			webserver, filename, client_data, cached = parse_request(message, host)
			if cached:
				host = webserver
			# multi-threading
			thread.start_new_thread(proxy_thread, (tcpCliSock, client_data, filename, webserver, cached))
		except KeyboardInterrupt:
			tcpCliSock.close()
			tcpSerSock.close()
			print "\n Proxy Server shutting down"
			sys.exit(2)

'''
thread main function to create a proxy_socket to connect with remote server,
send conditional GET and send responses back to client with different approaches
for different response status code and cached states
'''
def proxy_thread(tcpCliSock, client_data, filename, webserver, cached):
	try:
		cache_path, last_modified = get_log(filename)
		proxy_socket = socket(AF_INET, SOCK_STREAM) # Fill in start. # Fill in end.
		proxy_socket.connect((webserver, 80))
		proxy_socket.send(client_data)
		reply = proxy_socket.recv(BUFFER_SIZE) # conditional GET response
		responses = reply.splitlines()
		status = responses[0].split(' ')[1] # response status code like 200, 304, 404
		print("Response:")
		print("status code:", status)

		# HTTP response message for file not found
		if '404' == status:
			print "404 Not Found"
			tcpCliSock.send(reply)

		# If there is a cache(last_modified is not None) with status code 304, 
		# it shows that we don't need to update cache and we can directly read responses
		# from cache and send them back to client without requesting to remote server anymore
		elif last_modified and '304' == status:
			print "304 Not Modified"
			print "Read from cache"
			# Check wether the file exist in the cache
			f = open(cache_path, "r")
			outputdata = f.read(BUFFER_SIZE)
			while outputdata:
				tcpCliSock.send(outputdata)
				outputdata = f.read(BUFFER_SIZE)
			f.close()
			print "Read from cache done"

		# If there is no cache or cache is not most up-to-date version, but it's refered file
		# so that we don't need to cache it just send response back to client from remote server
		elif not cached:
			print "Referer and not caching this"
			tcpCliSock.send(reply)
			response_data = recv_timeout(proxy_socket)
			tcpCliSock.send(response_data)
			print "Referer done"

		# If there is no cache or cache is not most up-to-date version and it is our requested file,
		# then we cache the file while sending response back to client from remote server
		else:
			print "Cache the file and send response from remote server"
			tmpFile = open(cache_path,"wb")
			tcpCliSock.send(reply)
			tmpFile.write(reply)
			response_data = recv_timeout(proxy_socket)
			tcpCliSock.send(response_data)
			tmpFile.write(response_data)
			update_log(filename) # update file last_modified_time
			tmpFile.close()
			print "Cache file and get response from remote server done"

		proxy_socket.close()
		tcpCliSock.close()
		return

	except Exception as e:
		proxy_socket.close()
		tcpCliSock.close()
		print e
		return

# socket.recv(size) is a blocking call, and my code will wait for a long time for recv()
# so I add this timeout function to return from recv() and solve this problem
def recv_timeout(proxy_socket, timeout=2):
    proxy_socket.setblocking(0)
    response = []; data = ''; begin = time.time()
    while 1:
        # Got some data, then break after wait sec
        if response and time.time() - begin > timeout:
            break
        # Got no data at all, wait a little longer
        elif time.time() - begin > timeout*2:
            break
        try:
            data = proxy_socket.recv(BUFFER_SIZE)
            if data:
                response.append(data)
                begin = time.time()
            else:
                time.sleep(0.1)
        except:
            pass
    return ''.join(response)

if __name__ == '__main__':
  	main()