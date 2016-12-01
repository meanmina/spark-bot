# Generic bot
RESTful api for spark bots

Setup
1. Change the name of the app in app.json before deploying in heroku
2. bot\_helpers.py needs your spark bot's personId to interract with spark
3. After deploying you must send an access token before interacting on spark
    curl - H "Content-Type: application/json" -X POST -d '{"token": "<bots token>"}' https://\<bot\_name\>.herokuapp.com/token
