import socket
import sys
from datetime import datetime

def getPort():
    """Gets port to bind to from user and checks it is in the right range"""
    port = int(input("Please provide a port number between 1024 and 64000 including\n"))
    if port < 1024 or port > 64000:
        print("Port number must be between 1024 and 64000 including\nSystem terminated")
        sys.exit()
    print("successful port declaration")
    return port
    
def getTime():
    """Gets the current time"""
    now = datetime.now()
    return now.strftime("%H:%M:%S")

def fileNameLen(msg):
    """Gets the length of the filename from bytearray"""
    return int.from_bytes(msg[3:5], 'big')

def validate(msg):
    """Checks that the request from the client has the correct parameters
    in its header"""
    validated = True
    byte_1 = int.from_bytes(msg[0:2], 'big')
    byte_2 = int.from_bytes(msg[2:3], 'big')
    file_name_len = fileNameLen(msg)
    
    #checks filename is of the correct size
    if file_name_len < 1:
        validated = False
    if file_name_len > 1024:
        validated = False    
    #checks parameters are correct
    if not (byte_1 == 0x497E and byte_2 == 1):
        validated = False
    return validated
    
def getFile(package, length):
    """gets the data from the requested file"""
    status = 1
    #gets the filename from the request
    file_name = bytes(package[0:length]).decode('utf-8')
    
    #trys to open the file and reads the data into bytearray.
    #if file cannot be opened or doesnt exist status is returned as 0.
    try:
        file = open(file_name, 'rb')
        contents = bytearray(file.read().strip())
        file.close()
    except Exception as e:
        print("could not open file: {}. {}".format(file_name, e))
        contents = None
        status = 0
    return contents, status

def prepareFileResponse(package, file_name_len):
    """prepares the response message from the server"""
    #gets data from the file if the file exists
    contents, status = getFile(package, file_name_len)
    
    #forms the reponse header
    b = bytearray()
    b[0:2] = (0x497E).to_bytes(2, byteorder='big')
    b[2:3] = (2).to_bytes(1, byteorder='big')
    b[3:4] = status.to_bytes(1, byteorder='big')
    if status == 0:
        b[4:8] = (0).to_bytes(4, byteorder='big')
    #adds the contents of the file if status is 1
    elif status == 1:
        b[4:8] = len(contents).to_bytes(4, byteorder='big')
        b += contents
    return b

    
def main():
    """main function which provides logical flow of server"""
    #gets the port to bind to from the user
    port = getPort()
    
    #creates an ipv4 TCP socket and checks for errors in creation
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("Socket created successfully")
    except socket.error as e:
        print("socket creation failed: {}".format(e))
        sys.exit()
    
    #binds the socket to a certain port which can connect to any ip address
    #due to the '' parameter. Checks for errors in binding
    try:
        s.bind(('', port))
        print("socket bound to {}".format(port))
    except socket.error as e:
        print("socket not bound: {}\nSystem terminated".format(e))
        s.close()
        sys.exit()
    
    #sets the socket to listen to the port it is bound to
    #checks for errors
    try:
        s.listen()
        print("socket is listening")
    except:
        print("socket listen failed\nSystem terminated")
        s.close()
        sys.exit()
    
    #creates a infinate loop for the server to connect to clients
    while True:
        #accept a connection
        conn, addr = s.accept()
        
        #set timeout for connection socket created by .accept()
        conn.settimeout(1.0)
        print("{} connection request from: {}".format(getTime(), addr))
        
        #recieve the request header from socket buffer,
        #check for errors in recieving
        try:
            msg = bytearray(conn.recv(5))
        except socket.timeout as e:
            print("socket timed out receiving data: {}".format(e))
            conn.close()
            continue
        print(msg)
        
        #check that the header parameters are correct from the client
        validated = validate(msg)
        
        # if the header is correct recieve the filename from the buffer
        #and formulate response
        if validated:
            print("validated connection")
            file_name_len = fileNameLen(msg)
            
            #recieve from the socket buffer only the number of bytes needed
            #to recieve the correct filename
            try:
                package = bytearray(conn.recv(file_name_len))
            except socket.timeout as e:
                print("socket timed out receiving data: {}".format(e))
                conn.close()
                continue
            
            #prepare the response with file data
            #if the file exists in the server    
            response = prepareFileResponse(package, file_name_len)
            print("response length: {}".format(len(response)))
            
            #send the reponse to the client
            try:
                sent = conn.send(response)
                
                #if the entire message isn't sent in one go
                #keep sending until correct number of bytes are sent
                while sent < len(response):
                    sent1 = conn.send(response[sent:])
                    sent += sent1
                print("bytes sent to {}: {}".format(addr, sent))
            except socket.error as e:
                print("Error sending response: {}".format(e))
                conn.close()
                continue
        #close the connection and loop
        conn.close()
        
main()