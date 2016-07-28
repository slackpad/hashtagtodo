HashtagTodo
-----------

HashtagTodo is an application that manages your todos inside of a Google Calendar. You make items with `#todo` in the summary and the back end will pick them up and start managing them. If items aren't checked off on the day they are due then they will get rolled forward at midnight.

Getting Started
---------------

This is designed to run in Google App Engine. You'll need to set up an account there in order to run in production. Note that the Google Calendar push notifications require you to enable SSL.

The only step required before running in development or production is to edit the [`todo/config.py`](https://github.com/slackpad/hashtagtodo-open/blob/master/todo/config.py) file and supply the required values there. It's recommended that you don't check this file in with real values, since it contains sensitive information. Once that's filled in, run a development server to test your changes.

Running a Development Server
----------------------------

Just run `make develop` and it will start a server that will watch for files changes as you edit and apply the changes immediately.

If you have the right credentials, `make production` will deploy the application to Google App Engine.
