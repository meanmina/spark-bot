# Generic bot
RESTful api for spark bots

Setup
1. bot\_helpers.py needs your spark bot's personId to interract with spark
2. You must send an access token before interacting on spark
    curl - H "Content-Type: application/json" -X POST -d '{"token": "<bots token>"}' https://\<bot\_name\>.herokuapp.com/token
