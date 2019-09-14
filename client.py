import os
import sys
import socket


class Client:
    def __init__(self, addr, port, data_port):
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = addr
        self.port = port
        self.cwd = os.getcwd()
        self.conectou = False
        self.data_port = data_port

    def conectar(self):
        server_addr = (self.addr, self.port)
        self.sock.connect(server_addr)
        print("Conectado a", self.addr, ":", self.port)

    def start(self):
        try:
            self.conectar()
        except Exception:
            self.close()

        while True:
            try:
                command = input("Digite comando:")
            except KeyboardInterrupt:
                self.close()
            cmd = command[:4].strip().lower()
            path = command[4:].strip()
            try:
                self.sock.send(command.encode())
                data = self.sock.recv(1024).decode()
                print(data)
                if cmd == 'quit':
                    self.close()
                elif 'ls' in cmd:
                    if data and (data[0:3] == '000'):
                        if 'ls' in cmd:
                            cmd = 'ls'
                        func = getattr(self, cmd)
                        func(path)
                        run = True
                        while run:
                            data = self.sock.recv(1024).decode()
                            print(data)
                            if '111' in data or '110' in data:
                                run = False
                elif cmd == 'get' or cmd == 'put':
                    if data and (data[0:3] == '000'):
                        func = getattr(self, cmd)
                        func(path)
                elif 'cd' in cmd:
                    self.cwd = data[8:-4]
            except Exception as e:
                print(str(e))
                self.close()

    def connect_tcp(self):
        self.tcp.connect((self.addr, self.data_port))

    def ls(self, path):
        try:
            if not self.conectou:
                self.connect_tcp()
                self.conectou = True
            while True:
                dirlist = self.tcp.recv(1024).decode()
                if not dirlist:
                    break
                sys.stdout.write(dirlist)
                sys.stdout.flush()
        except Exception as e:
            print(str(e))

    def get(self, path):
        print("Copiando ", path, " do servidor")
        try:
            if not self.conectou:
                self.connect_tcp()
                self.conectou = True
            fname = os.path.join(self.cwd, path)
            f = open(fname, 'wb')
            msg = self.sock.recv(1024)
            print("Antes a", msg.decode())
            while msg.decode() != "111 Transferencia de arquivo completa":
                print("Recebendo arquivo ", msg.decode())
                f.write(msg)
                msg = self.sock.recv(1024)
        except Exception as e:
            print(str(e))
        finally:
            f.close()
            print(msg.decode())

    def put(self, path):
        print("Enviando copia", path, " para servidor")
        try:
            if not self.conectou:
                self.connect_tcp()
                self.conectou = True

            f = open(path, 'r')
            upload = f.read()
            while upload:
                self.tcp.send(upload.encode())
                upload = f.read()
        except Exception as e:
            print(str(e))
        finally:
            f.close()

    def close(self):
        print("Encerrando a sessao atual...")
        self.sock.close()
        print("Cessando execucao do cliente...")
        quit()


if __name__ == "__main__":
    addr = 'localhost'
    port = 2121
    data_port = 10020
    cliente = Client(addr, port, data_port)
    cliente.start()
