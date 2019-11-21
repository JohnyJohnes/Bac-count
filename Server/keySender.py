import socket
import time

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 33000))
while True:
    client.send("I am CLIENT\n")
    
    time.sleep(5)

client.close()
