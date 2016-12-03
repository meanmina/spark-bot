# Heroku spark bot template
Template for a RESTful api with most of the setup pre configured

## An example quick setup

1. Make a fork of this repo

2. Create a spark bot

3. Create a (free hobby-dev) heroku web app

4. Change the name field in app.json to match your heroku app name (probably optional)

5. Configure the Heroku environment variables as follows:
    
    TOKEN=**Your bot's access token**
    
    PERSON_ID=**Your bot's personId**

    ROOMS=**A list of rooms IDs** - your bot will say hello on startup

    ADMIN_TOKEN=**Your spark token** - so your bot can read all messages you can
    
6. Setup Heroku to autodeploy from pushes to your github repo
