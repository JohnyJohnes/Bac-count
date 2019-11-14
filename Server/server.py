# #!/usr/bin/env python

# import random
# import socket
# import select
# from time import gmtime, strftime
# from random import randint

# imgcounter = 1
# basename = "image%s.png"

# HOST = '127.0.0.1'
# PORT = 6666

# connected_clients_sockets = []

# server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# server_socket.bind((HOST, PORT))
# server_socket.listen(10)

# connected_clients_sockets.append(server_socket)

# while True:

#     read_sockets, write_sockets, error_sockets = select.select(
#         connected_clients_sockets, [], [])

#     for sock in read_sockets:

#         if sock == server_socket:

#             sockfd, client_address = server_socket.accept()
#             connected_clients_sockets.append(sockfd)

#         else:
#             try:

#                 data = sock.recv(4096)
#                 txt = str(data)

#                 if data:

#                     if data.startswith('SIZE'):
#                         tmp = txt.split()
#                         size = int(tmp[1])

#                         print('got size')

#                         sock.sendall("GOT SIZE")

#                     elif data.startswith('BYE'):
#                         sock.shutdown()

#                     else:

#                         myfile = open(basename % imgcounter, 'wb')
#                         myfile.write(data)

#                         data = sock.recv(40960000)
#                         if not data:
#                             myfile.close()
#                             break
#                         myfile.write(data)
#                         myfile.close()

#                         sock.sendall("GOT IMAGE")
#                         sock.shutdown()
#             except:
#                 sock.close()
#                 connected_clients_sockets.remove(sock)
#                 continue
#         imgcounter += 1
# server_socket.close()
import io
import socket
import picamera
import atexit


def camServer():

    while True:
        print("wait...")
        conn, addr = server_socket.accept()
        if conn:
            print(conn)
            print(addr)
            connection = conn.makefile('wb')
            break

    print("Connecting")
    try:
        stream = io.BytesIO()
        camera.capture(stream, 'jpeg')
        stream.seek(0)
        connection.write(stream.read())
        stream.seek(0)
        stream.truncate()
    finally:
        print("close connection")
        connection.close()


def onExit():
    connection.close()
    server_socket.close()
    print("exit")


with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)
    camera.start_preview()
    atexit.register(onExit)

    server_socket = socket.socket()
    server_socket.bind(('0.0.0.0', 8000))
    server_socket.listen(0)
    server_socket.setblocking(1)

    while True:
        camServer()
