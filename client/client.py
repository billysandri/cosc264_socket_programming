import socket
import sys
import os

def isFileLocal(file):
    """Checks whether the file exists"""
    return os.path.isfile(file)

def getInput():
    """Gets the ip address, port number of server and filename to retrieve from
       from the user"""
    
    #gets user input from the command line
    #checks that the right amount of parameters are entered
    inp = input("please enter a host name, port number of host and a filename you wish to retrieve (seperated by spaces)\n")
    try:
        addr, port, file = inp.split()
    except ValueError as e:
        print("Parameters entered incorrectly: {}\nSystem terminated".format(e))
        sys.exit()
    
    #gets the ip adress of the host if entered not in ip form
    try:
        address = socket.gethostbyname(addr)
        print("host resolved successfully")
    except socket.error as e:
        print("could not resolve host: {}".format(e))
    
    #checks that the port number is entered correcty
    port = int(port)
    if port < 1024 or port > 64000:
        print("Port number must be between 1024 and 64000 including\nSystem terminated")
        sys.exit()
    print("successful port declaration")
    
    #checks that the file doesn't exist locally
    #checks that the filename is the right length
    file_exists = isFileLocal(file)
    file_name = file.encode('utf-8')
    if file_exists:
        print("file found locally\nSystem terminated")
        sys.exit()    
    if len(file_name) < 1:
        print("filename too short")
        sys.exit()
    elif len(file_name) > 1024:
        print("filename too long to send")
        sys.exit()
        
    print("input successful")
    return address, port, file
    
def prepareFileRequest(file_name):
    """prepares the bytearray to be sent to server"""
    file_bytes = file_name.encode('utf-8')
    n = len(file_bytes)
    b = bytearray()
    b[0:2] = (0x497E).to_bytes(2, byteorder='big')
    b[2:3] = (0b00000001).to_bytes(1, byteorder='big')
    b[3:5] = n.to_bytes(2, byteorder='big')
    b[5:5+n] = file_bytes
    return b
    
def validateResponse(msg):
    """checks that the response from the server is formatted correctly"""
    validated = True
    byte_1 = int.from_bytes(msg[0:2], 'big')
    byte_2 = int.from_bytes(msg[2:3], 'big')
    byte_3 = int.from_bytes(msg[3:4], 'big')
    
    if not (byte_1 == 0x497E and byte_2 == 2 and (byte_3 == 0 or byte_3 == 1)):
        validated = False
    return validated

def writeFile(response, s, file_name):
    """Writes the file data given by the server to a local file"""
    #Checks if the server sent any file data
    is_data = (int.from_bytes(response[3:4], 'big') == 1)
    len_data = int.from_bytes(response[4:8], 'big')
    if is_data:
        try:
            file = open(file_name, 'wb')
        except:
            print("failed to open file\nSystem terminated")
            s.close()
            sys.exit()
        
        #Takes data from the socket buffer and writes it to a file.
        #Writes data at up to 4096 bytes at a time.
        #Error checks for socket read error, socket timeout and
        #writing to file error.
        #Keeps looping until data written to file is the same as 
        #amount as the length specified in response from server.
        byte_count = 0
        while byte_count < len_data:
            try:
                data = s.recv(4096)
                if len(data) == 0:
                    print("Packets lost in transit\nData loss in file")
                    s.close()
                    file.close
                    sys.exit()
                file.write(bytes(data))
                byte_count += len(data)
                print("{} bytes recieved from server".format(len(data)))
            except socket.timeout as e:
                print("socket timed out receiving data: {}".format(e))
                s.close()
                file.close()
                sys.exit()
            except socket.error as e:
                print("socket read failed: {}".format(e))
                s.close()
                file.close()
                sys.exit()
            except Exception as e:
                print("failed to write data: {}".format(e))
                s.close()
                file.close
                sys.exit()
                
        #checks if right amount of data recieved from server
        if byte_count == len_data:
            file.close()
            print("file successfully retrieved from server")
        elif byte_count > len_data:
            print("Extra data recieved file may have errors")
            file.close()
            s.close()
            sys.exit()
    #if no file data in response server couldn't find file or couldnt open it
    elif not is_data:
        print("file did not exist or could not be opened by server\nSystem terminated")
    return

def main():
    """Main function which provides logical flow of client"""
    #Get input from user
    ip, port, file_name = getInput()
    
    #creates an ipv4 TCP socket and check for errors in creation
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("socket created successfully")
    except socket.error as e:
        print("socket creation failed: {}".format(e))
        sys.exit()
    
    #connect to server and check for errors
    try:
        s.connect((ip, port))
        print("Successful connection")
    except socket.error as e:
        print("connection failed: {}".format(e))
        s.close()
        sys.exit()
    
    #prepare request to send to server.
    #send request to server
    b = prepareFileRequest(file_name)
    print("file request: {}".format(b))
    try:
        sent = s.send(b)
        print("{} bytes sent to server".format(sent))
    except socket.error as e:
        print("Error sending request: {}".format(e))
        s.close()
        sys.exit()

    #set timeout for socket if it takes too long to receive response from server
    s.settimeout(1.0)
    
    #receive response header from socket buffer
    try:
        response = bytearray(s.recv(8))
    except socket.timeout as e:
        print("socket timed out receiving data: {}".format(e))
        s.close()
        sys.exit()
    
    #check header has correct parameters
    validated = validateResponse(response)
    if not validated:
        print("response from server has errors\nSystem terminated")
        s.close()
        sys.exit()
    
    #write file data to file if file data exists
    writeFile(response, s, file_name)
    
    #close socket and exit system
    s.close()
    sys.exit()

main()