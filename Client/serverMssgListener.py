import socket
import time
import subprocess
serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serv.bind(('127.0.0.1', 33000))
serv.listen(5)
while True:
    conn, addr = serv.accept()
    while True:
        data = conn.recv(4096)
        if not data:
            break
        print("recieve")
        subprocess.call(['./camera.sh'])
        print(data)
        time.sleep(2)
    conn.close()
