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


class TServer(threading.Thread):
    def __init__(self, cliente, cliente_addr, local_ip, data_port):
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cliente = cliente
        self.cliente_addr = cliente_addr
        self.iniciou = False
        self.cwd = os.getcwd()
        self.data_address = (local_ip, data_port)
        threading.Thread.__init__(self)

    def tcp_inic(self):
        try:
            print("Criando conexao tcp em ", str(self.data_address), "...")
            self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp.bind(self.data_address)
            self.tcp.listen(5)
            print("Coxexao iniciada em", str(self.data_address))
            self.cliente.send("125 Conexao aberta, pode comecar a transferencia.\r\n".encode())
            return self.tcp.accept()
        except Exception as e:
            print("ERROR: ", str(e))
            print("Encerrando conexao")
            self.close_tcp()
            self.cliente.send("425: Nao e possivel realizar conexao.\r\n".encode())

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
                    if cmd[0:3] == 'get' or cmd[0:3] == 'put' or  cmd[0:3] == 'pwd':
                        func = getattr(self, cmd[:3].strip().lower())
                    elif cmd[0:5] == 'mkdir' or cmd[0:5] == 'rmdir' or cmd[0:5] == 'close' or cmd[0:5] == 'open' or cmd[0:5] == 'quit':
                        func = getattr(self, cmd[0:5].strip().lower())
                    elif cmd[0:6] == 'delete':
                        func = getattr(self, cmd[0:6].strip().lower())
                    elif cmd[0:2] == 'cd' or cmd[0:2] == 'ls':
                        func = getattr(self, cmd[0:2].strip().lower())
                    func(cmd)
                except AttributeError as e:
                    print("ERROR: Comando invalido")
                    self.cliente.send("550 Comando invalido.\r\n".encode())
        except Exception as e:
            print("EROOR: ", str(e))
            self.quit('')

    def quit(self, cmd):
        print("Fechando conexao ", str(self.cliente_addr))
        self.close_tcp()
        self.cliente.close()
        quit()

    def ls(self, cmd):
        print(self.cwd)
        if not self.iniciou:
            cliente_data, cliente_addr = self.tcp_inic()
            self.iniciou = True
        else:
            self.cliente.send("125 Conexao aberta, pode comecar a transferencia.\r\n".encode())
        try:
            listdir = os.listdir(self.cwd)
            if not len(listdir):
                max_length = 0
            else:
                max_length = len(max(listdir, key=len))

            header = '| %*s | %9s | %12s | %20s | %11s | %12s |' % (
                max_length, 'Name', 'Filetype', 'Filesize', 'Last Modified', 'Permission', 'User/Group')
            table = '%s\n%s\n%s\n' % ('-' * len(header), header, '-' * len(header))
            self.cliente.send(table.encode())

            for i in listdir:
                path = os.path.join(self.cwd, i)
                stat = os.stat(path)
                data = '| %*s | %9s | %12s | %20s | %11s | %12s |\n' % (
                    max_length, i, 'Directory' if os.path.isdir(path) else 'File', str(stat.st_size) + 'B',
                    time.strftime('%b %d, %Y %H:%M', time.localtime(stat.st_mtime))
                    , oct(stat.st_mode)[-4:], str(stat.st_uid) + '/' + str(stat.st_gid))
                self.cliente.send(data.encode())

            table = '%s\n' % ('-' * len(header))
            self.cliente.send(table.encode())

            self.cliente.send(" 226 Envio ok\r\n".encode())
        except Exception as e:
            print("ERROR: " , str(e))
            self.cliente.send("426 Conexao fechada, transferencia abortada\r\n".encode())
        finally:
            print("Comando finalizado")
            # cliente_data.close()
            # self.close_tcp()

    def pwd(self, cmd):
        msg = '257 \"%s\".\r\n' % self.cwd
        self.cliente.send(msg.encode())

    def cd(self, cmd):
        dest = os.path.join(self.cwd, cmd[3:].strip())
        if os.path.isdir(dest):
            self.cwd = dest
            msg = '250 OK \"%s\".\r\n' % self.cwd
            self.cliente.send(msg.encode())
        else:
            print("ERROR: Diretorio nao encontrado")
            msg = '550 \"' + dest + '\": No such file or directory.\r\n'
            self.cliente.send(msg.encode())

    def mkdir(self, cmd):
        path = cmd[6:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("501 Faltando <dirname>.\r\n".encode())
            else:
                os.mkdir(dirname)
                msg = '250 Directory criado: ' + dirname + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("Falha ao criar diretorio".encode())

    def rmdir(self, cmd):
        path = cmd[6:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("501 Faltando <dirname>.\r\n".encode())
            else:
                os.rmdir(dirname)
                msg = '250 Directory deleted: ' + dirname + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("Falha ao remover diretorio".encode())

    def delete(self, cmd):
        path = cmd[7:].strip()
        filename = os.path.join(self.cwd, path)
        try:
            if not path:
                self.cliente.send("501 Faltando <filename>.\r\n".encode())
            else:
                os.remove(filename)
                msg = '250 File deleted: ' + filename + '.\r\n'
                self.cliente.send(msg.encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("Falha ao deletar arquivo".encode())

    def put(self, cmd):
        path = cmd[4:].strip()
        if not path:
            self.cliente.send("501 Faltando <filename>.\r\n".encode())
            return
        fname = os.path.join(self.cwd, path)
        if not self.iniciou:
            cliente_data, cliente_addr = self.tcp_inic()
            self.iniciou = True
        else:
            self.cliente.send("125 Conexao aberta, pode comecar a transferencia.\r\n".encode())
        try:
            file_write = open(fname, 'w')
            print("poraaaaaaaaaaaaaa")
            while True:
                print("laalalalala")
                data = self.cliente.recv(4096)
                print("aaaaaaaaaaaaaaaa")
                if not data:
                    break
                file_write.write(str(data))

            self.cliente.send("226 Transferencia de arquivo completa.\r\n".encode())
        except Exception as e:
            print("ERROR: ", str(e))
            self.cliente.send("Falha ao enviar arquivo".encode())
        finally:
            print("Comando finalizado")
            # cliente_data.close()
            # self.close_tcp()
            file_write.close()

    def get(self, cmd):
        path = cmd[4:].strip()
        if not path:
            self.cliente.send("501 Faltando <filename>.\r\n".encode())
            return
        fname = os.path.join(self.cwd, path)
        print("11", fname, "---", self.cwd, "***", path)
        if not self.iniciou:
            cliente_data, cliente_addr = self.tcp_inic()
            self.iniciou = True
        else:
            self.cliente.send("125 Conexao aberta, pode comecar a transferencia.\r\n".encode())
        if not os.path.isfile(fname):
            self.cliente.send("550 Arquivo nao encontrado.\r\n".encode())
        else:
            try:
                file_read = open(fname, "r")
                data = file_read.read(1024)
                while data:
                    self.cliente.send(data.encode())
                    data = file_read.read(1024)
                self.cliente.send("226 Transferencia de arquivo completa.\r\n".encode())
            except Exception as e:
                print("ERROR: ", str(e))
                self.cliente.send("Conexao fechada, transferencia abortada".encode())
            finally:
                print("Comando finalizado")
                # cliente_data.close()
                # self.close_tcp()
                file_read.close()


class Server:
    def __init__(self, port, data_port):
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = '0.0.0.0'
        self.port = port
        self.data_port = data_port

    def start_tcp(self):
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = (self.address, self.port)
        try:
            print("Criando conexao TCP em: ", str(self.address), ":", self.port)
            self.tcp.bind(server_address)
            self.tcp.listen(5)
            print("Servidor conectado")
        except Exception as e:
            print("Falha em criar servidor: ", str(e))
            quit()

    def start(self):
        self.start_tcp()
        try:
            while True:
                print("Esperando conexao")
                cliente, cliente_addr = self.tcp.accept()
                thread = TServer(cliente, cliente_addr, self.address, self.data_port)
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("Fechando conexao TCP")
            self.tcp.close()
            quit()


if __name__ == "__main__":
    port = 2121
    data_port = 10020
    server = Server(port, data_port)
    server.start()
