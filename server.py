# Comandos
#   cd <dirname>: altera o diretorio atual
#   ls [dirname]: lista conteudo do diretorio atual
#   pwd: exibe path do diretorio atual
#   mkdir <dirname>: cria diretorio dirname
#   rmdir <dirname>: remove diretorio dirname e seu conteudo
#   get <filename>: realiza copia do arquivo filename do servidor para pasta local
#   put <filename>: envia uma copia do filename localizado na máquina local para o servidor
#   delete <filename>: remove o arquivo remoto filename
#   close: encerra sessão atual
#   open <server>: conectar ao host server
#   quit: encerra sessão atual e cessa execução do cliente

import os
import threading
import socket
import time
import shutil


class TServer(threading.Thread):
    def __init__(self, cliente, cliente_addr, local_ip, data_port):
        self.cliente = cliente
        self.cliente_addr = cliente_addr
        self.iniciou = False
        self.cwd = os.getcwd()
        self.server_cwd = os.getcwd()
        self.data_address = (local_ip, data_port)
        threading.Thread.__init__(self)

    def tcp_inic(self):
        try:
            print("Criando conexao tcp em ", str(self.data_address), "...")
            self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp.bind(self.data_address)
            self.tcp.listen(5)
            print("Coxexao iniciada em", str(self.data_address))
            self.cliente.send("000 Conexao aberta, pode comecar a transferencia.\r\n".encode())
            return self.tcp.accept()
        except Exception as e:
            print("ERROR: ", str(e))
            print("Encerrando conexao")
            self.close_tcp()
            self.cliente.send("999: Nao e possivel realizar conexao.\r\n".encode())

    def close_tcp(self):
        print("Encerrando conexao...")
        self.tcp.close()

    def run(self):
        try:
            print("Cliente conectado: ", str(self.cliente_addr))
            while True:
                cmd = self.cliente.recv(1024).decode()
                if not cmd:
                    break
                print("Comando ", cmd, "enviado de ", str(self.cliente_addr))
                try:
                    if cmd[0:3] == 'get' or cmd[0:3] == 'put' or cmd[0:3] == 'pwd':
                        func = getattr(self, cmd[:3].strip().lower())
                        func(cmd)
                    elif cmd[0:5] == 'mkdir' or cmd[0:5] == 'rmdir' or cmd[0:5] == 'close' or cmd[0:5] == 'open' or cmd[0:5] == 'quit':
                        func = getattr(self, cmd[0:5].strip().lower())
                        func(cmd)
                    elif cmd[0:6] == 'delete':
                        func = getattr(self, cmd[0:6].strip().lower())
                        func(cmd)
                    elif cmd[0:2] == 'cd' or cmd[0:2] == 'ls':
                        func = getattr(self, cmd[0:2].strip().lower())
                        func(cmd)
                    else:
                        self.cliente.send("110 Comando invalido.\r\n".encode())
                except AttributeError as e:
                    print("ERROR: Comando invalido")
                    self.cliente.send("110 Comando invalido.\r\n".encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.quit('')

    def cd(self, cmd):
        dest = os.path.join(self.cwd, cmd[3:].strip())
        if os.path.isdir(dest):
            self.cwd = dest
            msg = '111 OK \"%s\".\r\n' % self.cwd
            self.cliente.send(msg.encode())
        else:
            print("ERROR 110: Diretorio nao encontrado")
            msg = '110  Diretorio nao encontrado.\r\n'
            self.cliente.send(msg.encode())

    def ls(self, cmd):
        pasta = cmd[3:].strip()
        if len(pasta) == 0:
            pasta = self.cwd
        print(pasta)
        cliente_data, cliente_addr = self.tcp_inic()
        try:
            listdir = os.listdir(pasta)
            if not len(listdir):
                max_length = 0
            else:
                max_length = len(max(listdir, key=len))

            header = '| %*s | %9s | %12s | %20s | %11s | %12s |' % (
                max_length, 'Name', 'Filetype', 'Filesize', 'Last Modified', 'Permission', 'User/Group')
            table = '%s\n%s\n%s\n' % ('-' * len(header), header, '-' * len(header))
            self.cliente.send(table.encode())

            for i in listdir:
                path = os.path.join(pasta, i)
                stat = os.stat(path)
                data = '| %*s | %9s | %12s | %20s | %11s | %12s |\n' % (
                    max_length, i, 'Directory' if os.path.isdir(path) else 'File', str(stat.st_size) + 'B',
                    time.strftime('%b %d, %Y %H:%M', time.localtime(stat.st_mtime))
                    , oct(stat.st_mode)[-4:], str(stat.st_uid) + '/' + str(stat.st_gid))
                self.cliente.send(data.encode())

            table = '%s\n' % ('-' * len(header))
            self.cliente.send(table.encode())

            self.cliente.send(" 111 Envio ok\r\n".encode())
        except Exception as e:
            print("ERROR 110: " , str(e))
            self.cliente.send("110 Diretorio nao encontrado\r\n".encode())
        finally:
            print("Comando finalizado")
            self.close_tcp()

    def open(self, cmd):
        self.cliente.send("Aberto".encode())

    def close(self, cmd):
        self.cliente.send("Fechado".encode())

    def pwd(self, cmd):
        msg = '111 \"%s\".\r\n' % self.cwd
        self.cliente.send(msg.encode())

    def mkdir(self, cmd):
        path = cmd[6:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("101 Faltando <dirname>.\r\n".encode())
            else:
                os.mkdir(dirname)
                msg = '001 Diretorio criado: ' + dirname + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("110 Diretorio ja existente".encode())

    def rmdir(self, cmd):
        path = cmd[6:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("101 Faltando <dirname>.\r\n".encode())
            else:
                shutil.rmtree(dirname, ignore_errors=True)
                msg = '001 Diretorio removido: ' + dirname + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("110 Diretorio inexistente".encode())

    def get(self, cmd):
        path = cmd[4:].strip()
        if not path:
            self.cliente.send("101 Faltando <filename>.\r\n".encode())
            return
        fname = os.path.join(self.server_cwd, path)
        cliente_data, cliente_addr = self.tcp_inic()
        if not os.path.isfile(fname):
            self.cliente.send("110 Arquivo nao encontrado.\r\n".encode())
        else:
            try:
                file_read = open(fname, "rb")
                data = file_read.read(1024)
                while data:
                    self.cliente.send(data)
                    data = file_read.read(1024)
                file_read.close()
                self.cliente.send("111 Transferencia de arquivo completa".encode())
            except Exception as e:
                print("ERROR: ", str(e))
                self.cliente.send("Conexao fechada, transferencia abortada".encode())
            finally:
                print("Comando finalizado")
                cliente_data.close()
                self.close_tcp()

    def put(self, cmd):
        path = cmd[4:].strip()
        if not path:
            self.cliente.send("101 Faltando <filename>.\r\n".encode())
            return
        fname = os.path.join(self.server_cwd, path)
        cliente_data, cliente_addr = self.tcp_inic()
        try:
            file_write = open(fname, 'wb')
            msg = self.cliente.recv(1024)
            while msg.decode() != "111 Transferencia de arquivo completa":
                file_write.write(msg)
                print("Recebendo arquivo ")
                msg = self.cliente.recv(1024)
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("Falha ao enviar arquivo".encode())
        finally:
            print("Comando finalizado")
            cliente_data.close()
            self.close_tcp()
            file_write.close()

    def delete(self, cmd):
        path = cmd[7:].strip()
        filename = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("101 Faltando <filename>.\r\n".encode())
            else:
                os.remove(filename)
                msg = '010 File deleted: ' + filename + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("011 Arquivo inexistente".encode())

    def quit(self, cmd):
        print("Fechando conexao ", str(self.cliente_addr))
        self.close_tcp()
        self.cliente.close()
        quit()


class Server:
    def __init__(self, port, data_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '0.0.0.0'
        self.port = port
        self.data_port = data_port

    def start_tcp(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = (self.address, self.port)
        try:
            print("Criando conexao TCP em: ", str(self.address), ":", self.port)
            self.sock.bind(server_address)
            self.sock.listen(5)
            print("Servidor conectado")
        except Exception as e:
            print("Falha em criar servidor: ", str(e))
            quit()

    def start(self):
        self.start_tcp()
        try:
            while True:
                print("Esperando conexao")
                cliente, cliente_addr = self.sock.accept()
                thread = TServer(cliente, cliente_addr, self.address, self.data_port)
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("Fechando conexao TCP")
            self.sock.close()
            quit()


if __name__ == "__main__":
    port = 2121
    data_port = 10001
    server = Server(port, data_port)
    server.start()
