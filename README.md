# Heroku spark bot template
Template for a RESTful api with most of the setup pre configured

## An example quick setup

1. Make a fork of this repo

2. Create a spark bot

3. Create a (free hobby-dev) heroku web app

4. Change the name field in app.json to match your heroku app name (probably optional) AND targetUrl in create_webhook()

5. Configure the Heroku environment variables as follows:
    
    TOKEN=**Your bot's access token**
    
    PERSON_ID=**Your bot's personId**

    ADMIN_ROOM=**An admin room ID** - your bot will use this space for persistent storage

    ADMIN_ID=**Your personal spark ID** - So your bot knows when you're talking to it

    ADMIN_TOKEN=**Your personal spark token** - so your bot can read all the messages you can
    
6. (optional) Setup Heroku to autodeploy from pushes to your github repo

7. Deploy Heroku instance

8. Add bot into a room and type "@<bot_name> hook me up". This registers a webhook on your spark account to send all messages seen in this room to the bot.
