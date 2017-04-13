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
        self.rest_api.router.add_post('/messages', self.post_message)
        self.rest_api.router.add_static('/images/', './images/')
        self.rest_api.router.add_get('/ws', self.websocket_handler)

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
        ws = web.WebSocketRewsponse()
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
