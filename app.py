#!/usr/bin/python3
from sys import argv
from server import Server


if __name__ == '__main__':
    host = '0.0.0.0'
    port = int(argv[1])
    app = Server(host, port)
    app.start()
