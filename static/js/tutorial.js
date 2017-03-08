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
    this.offerMade = Math.random() >= 0.5;
    this.reaction = false;
    
    this.wage = 12;
    this.finalWage = 12;
    this.bonus = 4;

    this.contract = Math.random() >= 0.5;
    this.accept = true;
    this.effortLevel = Math.random() >= 0.5 ? 'Low' : 'High';
    this.action = '';
    this.oid = url.substring(url.length - 26, url.length - 2);
});

tutorialApp.controller('TutorialController', ['$scope', '$window', 'dataModel', '$location', '$rootScope',
    function ($scope, $window, dataModel, $location, $rootScope) {
        $scope.game = {};
        $scope.game.continue = true;

        $scope.game.newPage = function(page){
            $window.location.assign("/tutorial1/user/" + oid + "#/" + page);
        }

        $scope.game.finishGame = function(){
            $window.location.assign("/instructionsemployee?oid=" + oid);
        }

        $scope.game.setContract = function(offer) {
            //true = A, false = B
            dataModel.contract = offer;
        }

        $scope.game.setAccept = function(response) {
            dataModel.accept = response;
        }

        $scope.game.setEffort = function(level) {
            dataModel.effortLevel = level;
        }

        $scope.game.setAction = function(act) {
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
            console.log("hit");
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

        $scope.game.print = function() {
            console.log("got it");
        }

        $scope.game.sendContract = function() {
            console.log(dataModel.stage);
            dataModel.stage = "contract";
            $scope.game.nextPage();

            if (dataModel.contract) {dataModel.varWage = false;}
            else if (!dataModel.varWage) {dataModel.offerMade = false;}
        }

        $scope.game.sendAction = function() {
            $scope.game.nextPage();
        }

        $scope.game.nextPage = function() {
            var employer = dataModel.role == "employer";
            console.log(dataModel.stage)
            var page = "";            

            if (dataModel.stage === "init") {
                dataModel.wage = dataModel.lowBase ? 12 : 16;
                dataModel.finalWage = dataModel.wage;
                page = employer ? '2' : 'wait';
                dataModel.stage = "contract";
            }
            else if (dataModel.stage === "contract") {
                console.log("effort Stage");
                page = employer ? '4' : '3';
                console.log(page);
                dataModel.stage = "effort";
            }
            else if (dataModel.stage === "effort" && dataModel.varWage && dataModel.offerMade && dataModel.accept && ((dataModel.lowBase && dataModel.effortLevel === 'High') || (!dataModel.lowBase && dataModel.effortLevel === 'Low'))) {
                dataModel.reaction = true;
                //console.log("reaction");
                page = employer ? '4' : 'wait';
                dataModel.stage = "action";
            }
            else {
                page = '5';
                dataModel.stage = "finish";
                var payment = employer ? 40 - dataModel.wage : dataModel.wage;

            }

            $scope.game.newPage(page);
        }

        
    }]);


