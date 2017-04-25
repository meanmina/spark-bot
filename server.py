#!/usr/bin/python3
'''
    Backend webapi for the ll bot
'''
import os
import psycopg2
from urllib.parse import urlparse
from aiohttp import web, WSMsgType
from backend import MessageHandler
from bot_helpers import get_message_info
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402


class Server:

    def __init__(self, host, port):
        self.host = host
        self.port = port

        url = urlparse(os.environ["DATABASE_URL"])
        db_conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        self.backend = MessageHandler(db_conn)

        self.rest_api = web.Application()
        self.rest_api.router.add_get('/', self.index)
        self.rest_api.router.add_post('/messages', self.post_message)
        self.rest_api.router.add_static('/images/', './images/')
        self.rest_api.router.add_get('/ws', self.websocket_handler)

        # Becky stuff
        self.rest_api.router.add_get('/becky', self.graph_input)
        self.rest_api.router.add_post('/draw_graph', self.draw_graph)

    async def index(self, request):
        return web.Response(text='Hello from Aiohttp!')

    def start(self):
        ''' start the server '''
        web.run_app(self.rest_api, host=self.host, port=self.port)

    async def post_message(self, request):
        ''' Receive a message from a spark webhook '''
        data = await request.json()
        try:
            message_id = data['data']['id']
        except KeyError:
            return web.Response(status=400, text='expected message id')

        message_info = get_message_info(message_id)
        try:
            self.backend.parse_message(message_info)
        except Exception as err:
            print(err)
            return web.Response(status=500)
        return web.Response(status=200)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    ws.send_str(msg.data + '/answer')
            elif msg.type == WSMsgType.ERROR:
                print('ws connection closed with exception %s' % ws.exception())

        print('websocket connection closed')

        return ws

    async def graph_input(self, request):
        html = '''
        <!DOCTYPE html>
        <html>
        <body>
            Choose which data to draw blant-altman plot for.<br>
            Accepted data sets are: observed, formula_1, formula_2, formula_3, and formula_4
            <br><br>
            <form action="/draw_graph" method="post">
                First formula:<br>
                <input id="f1" name="f1" type="text" value="formula_1">
                <br><br>
                Second formula:<br>
                <input id="f2" name="f2" type="text" value="formula_2">
                <br><br>
                <input type="submit" value="Draw">
            </form>
            <br><br>
        </body>
        </html>
        '''
        return web.Response(
            status=200, reason='OK', headers={'Content-Type': 'text/html'},
            text=html
        )

    async def draw_graph(self, request):
        html = '''
        <html>
        <body>
        {}
        </body>
        </html>
        '''

        data = await request.post()
        with open('axes.json', 'r') as fo:
            axes = json.load(fo)

        try:
            f1 = [float(n) for n in axes[data['f1']]]
            f2 = [float(n) for n in axes[data['f2']]]
        except KeyError:
            return web.Response(
                status=200, reason='OK', headers={'Content-Type': 'text/html'},
                text=html.format(
                    'Invalid data-set names {f1} and {f2}<br><br>'
                    '<a href="/becky">back</a>'.format(**data)
                )
            )

        bland_x = [(f1[i] + f2[i]) / 2 for i in range(len(f1))]
        bland_y = [f1[i] - f2[i] for i in range(len(f1))]

        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(bland_x, bland_y, 'bo')
        y_mean = np.mean(bland_y)
        ax.plot([0, 35], [y_mean, y_mean], 'g-')
        plt.savefig('images/graph.png')
        plt.close(fig)
        return web.Response(
            status=200, reason='OK', headers={'Content-Type': 'text/html'},
            text=html.format(
                'Success! Your graph can be seen <a href="/images/graph.png">here</a>'
            )
        )
