'use strict';

var tutorialApp = angular.module('tutorialApp', ['ngRoute']);

var protocols = ["websocket", "xdr-streaming", "xhr-streaming", "xdr-polling", "xhr-polling", "iframe-eventsource"];
var options = {protocols_whitelist: protocols, debug: true, jsessionid: false};

var url = window.location.href;
var oid = url.substring(url.length - 24, url.length);



tutorialApp.config(['$routeProvider',
    function ($routeProvider) {
        $routeProvider.
        when('/', {
            templateUrl: '/static/game/start.html',
            controller: 'TutorialController'
        }).
        when('/2', {
            templateUrl: '../../static/game/2.html',
            controller: 'TutorialController'
        }).
        when('/3', {
            templateUrl: '../../static/game/3.html',
            controller: 'TutorialController'
        }).
        when('/4', {
            templateUrl: '../../static/game/4.html',
            controller: 'TutorialController'
        }).
        when('/5', {
            templateUrl: '../../static/game/5.html',
            controller: 'TutorialController'
        }).
        when('/wait', {
            templateUrl: '../../static/game/wait.html',
            controller: 'TutorialController'
        }).
        when('/finish', {
            templateUrl: '../../static/game/finish.html',
            controller: 'TutorialController'
        }).
        otherwise({
            redirectTo: '/error'
        });
    }]);

tutorialApp.service("dataModel", function() {
    this.role = "employer";
    this.stage = "init";
    this.lowBase = Math.random() >= 0.5;
    this.varWage = Math.random() >= 0.5;
    this.offerMade = true;
    this.reaction = false;
    
    this.wage = 12;
    this.finalWage = 12;
    this.bonus = 4;

    this.contract = null;
    this.accept = true;
    this.effortLevel = Math.random() >= 0.5 ? 'Low' : 'High';
    this.action = '';

    this.counting = false;
    this.counter = 10;
    this.continue = true;

});

tutorialApp.controller('TutorialController', ['$scope', '$window', 'dataModel', '$interval', '$rootScope',
    function ($scope, $window, dataModel, $interval, $rootScope) {
        $scope.game = {};

        $scope.game.continue = dataModel.continue;
        $scope.game.hasRole = true;

        $scope.game.newPage = function(page){
            $window.location.assign("/tutorial1/user/" + oid + "#/" + page);
        }

        $scope.game.finishGame = function(){
            $window.location.assign("/instructionsemployee?oid=" + oid);
        }

        $scope.game.setContract = function(offer) {
            //true = A, false = B, 'none' = C

            $scope.game.continue = true;
            dataModel.contract = offer;
        }

        $scope.game.setAccept = function(response) {
            dataModel.accept = response;
        }

        $scope.game.setEffort = function(level) {
            dataModel.effortLevel = level;
        }

        $scope.game.setAction = function(act) {
            dataModel.continue = true;
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
            else if (dataModel.contract === 'none')
                return 'C';
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

        $scope.game.sendContract = function() {

            if (dataModel.contract === 'none') {dataModel.offerMade = false;}
            else if (dataModel.contract) {dataModel.varWage = false;}
            else if (!dataModel.varWage) {dataModel.offerMade = false;}

             
            $scope.game.nextPage();


        }

        $scope.game.sendAction = function() {
            if (dataModel.action === "reward")
                dataModel.finalWage += dataModel.bonus;
            if (dataModel.action === "penalize")
                dataModel.finalWage -= dataModel.bonus;

            $scope.game.nextPage();
        }

        $scope.game.nextPage = function() {
            var employer = dataModel.role == "employer";
            var page = "";
            dataModel.continue = false;

            dataModel.counter = 11;

          

            if (dataModel.stage === "init") {
                dataModel.wage = dataModel.lowBase ? 12 : 16;
                dataModel.finalWage = dataModel.wage;
                page = employer ? '2' : 'wait';
                dataModel.stage = "effort";
            }
            else if (dataModel.stage === "contract" && dataModel.offerMade) {
                page = employer ? '4' : '3';
                dataModel.stage = "effort";
            }
            else if (dataModel.stage === "effort" && dataModel.varWage && dataModel.offerMade && dataModel.accept && ((dataModel.lowBase && dataModel.effortLevel === 'High') || (!dataModel.lowBase && dataModel.effortLevel === 'Low'))) {
                dataModel.reaction = true;
                page = employer ? '4' : 'wait';
                dataModel.stage = "action";
            }
            else {
                page = '5';
                dataModel.stage = "finish";
                var payment = employer ? 40 - dataModel.wage : dataModel.wage;

            }

            $scope.game.newPage(page);
        };
        
    }]);

tutorialApp.controller('TimerController', ['$scope', '$window', 'dataModel', '$interval', '$rootScope',
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





