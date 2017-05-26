# Seed
Server-side

Webserver.py:

Webserver.py houses main backend infrastructure. It hosts three types of WebSocket connections. One for the session waiting room, one for the game waiting room, one for the game itself.

SessionConnection:
Simple, registers each person who loads the session waiting room page, decrements the count of people on the page each time a connection closes. Admin also creates this type of connection in order to send message to create a new session.

WaitingRoomConnection:
Similar to SessionConnection but also does matching algorithm and assigns game ids to people. More details in comments.

GameConnection:
Each connection has two clients, every message is bounced back to both with info on contract, effort level, etc. Pretty simple backend, more going on in Angular on the client side.

Handlers.py

Most HTML requests are resolved in handlers.py – except those that rely on Websocket Connection variables, specifically AdminHandler, for the admin screen. Pretty self explanatory, some leftover handlers from UbiquityLab.


Client-side

Templates

This folder holds the HTML templates for all pages besides quiz and game pages, which are in their own folders. Most use Angular controllers which will be described below.

Main.js

This controls most static pages that are not waiting room, quiz, or game pages. Main functions concern timer countdown and validating MTurk IDs




Session.js

Similar to waiting-room.js. Pulls parameters from URL. Opens a websocket connection. Sends parameter data in initial message. Manipulates DOM to show Proceed button when activate message is received.

Quiz.js

Controls quiz. Very self explanatory, more comments in code.

Tutorial.js and Tutorial2.js

Controls tutorial. Pretty messy as they are mostly copied from Game.js with minor changes. Can probably be combined into a single file. May even be combined into game.js perhaps.

Waiting-room.js

See session.js, nearly identical.

Game.js

A lot going on here. Opens a GameConnection WebSocket. Most data saved in dataModel rather than $scope as it persists through the loading of a new page. General data flow:
•	Client submits a decision
•	Function “sendEffortLevel” (or sendContract, sendAccept, etc) sends decision to server
•	Message bounces back to both parties in connection
•	Processing of message occurs in conn.onmessage and $scope.nextPage with different behavior depending on stage of game.
•	New page is loaded.
