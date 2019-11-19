import socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('127.0.0.1', 33000))
client.send("I am CLIENT\n")

client.close()
