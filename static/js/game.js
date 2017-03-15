'use strict';

var gameApp = angular.module('gameApp', ['ngRoute']);

var WAIT_MSG = 99,
    INIT_MSG = 100,
    ACTIVATE_MSG = 101,
    DEACTIVATE_MSG = 102,
    FULL_MSG = 103,
    CLOSE_MSG = 104,
    SESSION_MSG = 105,
    HEARTBEAT_MSG = 106,
    NO_CONFIG_MSG = 110,
    DUPLICATE_MSG = 111,
    ROLE_MSG = 112,
    READY_MSG = 113,
    CONTRACT_MSG = 114,
    EFFORT_MSG = 115,
    ACTION_MSG = 116,
    FINISH_MSG = 117;

var protocols = ["websocket", "xdr-streaming", "xhr-streaming", "xdr-polling", "xhr-polling", "iframe-eventsource"];
var options = {protocols_whitelist: protocols, debug: true, jsessionid: false};
var conn = new SockJS("https://intense-sands-23697.herokuapp.com/sockjs/game", null, options);
console.log("Client - connecting to game...");

var url = window.location.href;
var oid = url.substring(url.length - 24, url.length);


conn.onopen = function() {
    console.log("Client - connected");
    console.log("Client - protocol used: " + conn.protocol);
    // send INIT_MSG
    var init_msg = JSON.stringify({"type": INIT_MSG, "subject_id": oid});
    conn.send(init_msg);
    console.log("Client - INIT_MSG sent");

};

gameApp.config(['$routeProvider',
    function ($routeProvider) {
        $routeProvider.
        when('/', {
            templateUrl: '/static/game/start.html',
            controller: 'GameController'
        }).
        when('/2', {
            templateUrl: '../../static/game/2.html',
            controller: 'GameController'
        }).
        when('/3', {
            templateUrl: '../../static/game/3.html',
            controller: 'GameController'
        }).
        when('/3b', {
            templateUrl: '../../static/game/3b.html',
            controller: 'GameController'
        }).
        when('/4', {
            templateUrl: '../../static/game/4.html',
            controller: 'GameController'
        }).
        when('/5', {
            templateUrl: '../../static/game/5.html',
            controller: 'GameController'
        }).
        when('/wait', {
            templateUrl: '../../static/game/wait.html',
            controller: 'GameController'
        }).
        when('/finish', {
            templateUrl: '../../static/game/finish.html',
            controller: 'GameController'
        }).
        otherwise({
            redirectTo: '/error'
        });
    }]);

gameApp.service("dataModel", function() {
    this.role = "none";
    this.stage = "init";
    this.lowBase = false;
    this.varWage = true;
    this.offerMade = true;
    this.reaction = false;
    
    this.wage = 12;
    this.finalWage = 12;
    this.bonus = 4;

    this.contract = null;
    this.accept = null;
    this.effortLevel = '';
    this.action = '';

    this.counting = false;
    this.counter = 10;
    this.continue = false;
})

gameApp.controller('GameController', ['$scope', '$window', 'dataModel', '$location', '$rootScope',
    function ($scope, $window, dataModel, $location, $rootScope) {
        $scope.game = {};
        $scope.game.continue = dataModel.continue;
        $scope.game.wait = true;
        console.log($scope.game.continue);


        $scope.game.newPage = function(page){
                $window.location.assign("/game/user/" + oid + "#/" + page);
        }

        $scope.game.finishGame = function(){
            $window.location.assign("/payment?oid=" + oid);
        }

        $scope.game.setContinue = function(access) {
            //true = A, false = B
            $scope.game.continue = access;
        }

        $scope.game.setWait = function(wait) {
            console.log("no more waiting!");
            $scope.game.wait = wait;
        }

        $scope.game.setContract = function(offer) {
            //true = A, false = B
            $scope.game.continue = true;

            dataModel.contract = offer;
        }

        $scope.game.setAccept = function(response) {
            $scope.game.continue = true;

            dataModel.accept = response;
        }

        $scope.game.setEffort = function(level) {
            $scope.game.continue = true;

            dataModel.effortLevel = level;
        }

        $scope.game.setAction = function(act) {
            $scope.game.continue = true;

            dataModel.action = act;
        }

        $scope.game.getLowBase = function() {
            return dataModel.lowBase;
        }

        $scope.game.getVarWage = function() {
            return dataModel.varWage;
        }

        $scope.game.getOfferMade = function() {
            return dataModel.offerMade;
        }
        $scope.game.getWage = function() {
            return dataModel.wage;
        }

        $scope.game.getBonus = function() {
            return dataModel.bonus;
        }

        $scope.game.getContract = function() {
            if(dataModel.contract == null)
                return ''
            else if (dataModel.contract)
                return 'A';
            else
                return 'B';
        }

        $scope.game.getAccept = function() {
            if(dataModel.accept == null)
                return '';
            else if (dataModel.accept)    
                return 'accept';
            else
                return 'reject';
        }

        $scope.game.getAcceptVal = function() {
            return dataModel.accept;
        }

           $scope.game.getReactionVal = function() {
            return dataModel.reaction;
        }

        $scope.game.getEffort = function() {
            return dataModel.effortLevel;
        }

        $scope.game.getAction = function() {
            return dataModel.action;
        }

        $scope.game.getFinalWage = function() {
            return dataModel.finalWage;
        }

        $scope.game.nextPage = function() {
            var employer = dataModel.role == "employer";

            $scope.game.continue = false;
            dataModel.counter = 11;


            var page = "";
            if (dataModel.stage === "init") {
                dataModel.wage = dataModel.lowBase ? 12 : 16;
                dataModel.finalWage = dataModel.wage;
                page = employer ? '2' : 'wait';
                $scope.game.wait = !employer;

                dataModel.stage = "contract";
            }
            else if (dataModel.stage === "contract" && dataModel.offerMade) {
                page = employer ? 'wait' : '3';
                $scope.game.wait = employer;

                dataModel.stage = "effort";
            }
            else if (dataModel.stage === "accept" && dataModel.accept) {
                page = employer ? 'wait' : '3b';
                $scope.game.wait = employer;

                dataModel.stage = "effort";
            }
            else if (dataModel.stage === "effort" && dataModel.varWage && dataModel.offerMade && dataModel.accept && ((dataModel.lowBase && dataModel.effortLevel === 'High') || (!dataModel.lowBase && dataModel.effortLevel === 'Low'))) {
                dataModel.reaction = true;
                page = employer ? '4' : 'wait';
                $scope.game.wait = !employer;

                dataModel.stage = "action";
            }
            else {
                page = '5';
                dataModel.stage = "finish";
                var payment = employer ? 40 - dataModel.wage : dataModel.wage;
                conn.send(JSON.stringify({"type": FINISH_MSG,
                                        "role": dataModel.role, 
                                        "wage": dataModel.wage,
                                        "contract": dataModel.contract, 
                                        "accept": dataModel.accept, 
                                        "effortLevel": dataModel.accept ? dataModel.effortLevel : 'None', 
                                        "action": dataModel.action, 
                                        "payment": payment}));

            }

            $scope.game.newPage(page);
        }

        $scope.game.sendContract = function() {
            if(dataModel.contract) {dataModel.varWage = false;}
            else if (!dataModel.varWage) {dataModel.offerMade = false;}
            console.log(JSON.stringify({"type": CONTRACT_MSG, "contract": dataModel.contract, "varWage": dataModel.varWage, "offerMade": dataModel.offerMade}));
            conn.send(JSON.stringify({"type": CONTRACT_MSG, "contract": dataModel.contract, "varWage": dataModel.varWage, "offerMade": dataModel.offerMade}))
        }

        $scope.game.sendAccept = function() {
            dataModel.stage = "accept";
            if (!dataModel.accept) {
                dataModel.finalWage = 0;
                conn.send(JSON.stringify({"type": EFFORT_MSG, "accept": dataModel.accept,"effortLevel": dataModel.effortLevel}))
            }
            $scope.game.nextPage();
        }

        $scope.game.sendEffortLevel = function() {
            conn.send(JSON.stringify({"type": EFFORT_MSG, "accept": dataModel.accept,"effortLevel": dataModel.effortLevel}))
        }

        $scope.game.sendAction = function() {
            conn.send(JSON.stringify({"type": ACTION_MSG, "action": dataModel.action}))
        }
 
        conn.onmessage = function(e) {
            var msg = JSON.parse(e.data);
            var type = parseInt(msg.type);

            if (type === ROLE_MSG) {
                var role = msg.role;
                console.log("Client has role:" + role);
                dataModel.role = role;
            }
            else if (type === READY_MSG) {
                console.log("Participants ready");
               // console.log(msg.treatment)
                dataModel.lowBase = msg.lowBase;
                dataModel.varWage = msg.varWage;
                $scope.game.setContinue(true);
                $scope.game.setWait(false);
            }
            else if (type == CONTRACT_MSG) {
                dataModel.contract = msg.contract;
                dataModel.varWage = msg.varWage;
                dataModel.offerMade = msg.offerMade;
                dataModel.wage = dataModel.lowBase ? 12 : 16;

                $scope.game.nextPage();
            }
            else if (type == EFFORT_MSG) {
                var acceptStr = msg.accept ? "accept" : "reject";
                dataModel.accept = msg.accept;
                if (!dataModel.accept)
                    dataModel.finalWage = 0;
                dataModel.effortLevel = msg.effortLevel;
                $scope.game.nextPage();
            }
            else if (type == ACTION_MSG) {
                dataModel.action = msg.action;
                if (dataModel.action === "reward")
                    dataModel.finalWage += dataModel.bonus;
                if (dataModel.action === "penalize")
                    dataModel.finalWage -= dataModel.bonus;
                $scope.game.nextPage();
            }              
        };
    }]);

gameApp.controller('TimerController', ['$scope', '$window', 'dataModel', '$interval', '$rootScope',
    function ($scope, $window, dataModel, $interval, $rootScope) {
        $scope.game = {};

        $scope.game.counter = 10;

        $scope.game.timeUp = false;

        var stop;
        $scope.game.countdown = function(){
            dataModel.counting = true;
            if (angular.isDefined(stop) ) return;

            stop = $interval(function() {
                if ($scope.game.counter > 0) {
                    console.log($scope.game.counter);
                    dataModel.counter--;
                    $scope.game.counter = dataModel.counter;
                } else {
                    $scope.game.timerStop();
                }
            }, 1000); 
        };

        if (!dataModel.counting)
            $scope.game.countdown();

        $scope.game.timerStop = function() {
            $scope.game.timeUp = true;
            if (angular.isDefined(stop)) {
                $interval.cancel(stop);
                stop = undefined;
            }
        };

        $scope.$on('$destroy', function() {
          // Make sure that the interval is destroyed too
          $scope.game.timerStop();
        });

        
    }]);

