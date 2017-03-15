'use strict';

var quizApp = angular.module('quizApp', ['ngRoute']);

var url = window.location.href;
var oid = url.substring(url.length - 24, url.length);

quizApp.config(['$routeProvider',
    function ($routeProvider) {
        $routeProvider.
        when('/', {
            templateUrl: '/static/quiz/start.html',
            controller: 'QuizController'
        }).
        when('/0', {
            templateUrl: '../../static/quiz/0.html',
            controller: 'QuizController'
        }).
        when('/1', {
            templateUrl: '../../static/quiz/1.html',
            controller: 'QuizController'
        }).
        when('/2', {
            templateUrl: '../../static/quiz/2.html',
            controller: 'QuizController'
        }).
        when('/3', {
            templateUrl: '../../static/quiz/results.html',
            controller: 'QuizController'
        }).
        otherwise({
            redirectTo: '/error'
        });
    }]);

quizApp.service("dataModel", function() {
    this.correct = 0;
})

quizApp.controller('QuizController', ['$scope', '$window', 'dataModel', '$interval',
    function ($scope, $window, dataModel, $interval) {
        $scope.quiz = {};
        $scope.quiz.answers = ['Paris', 'Berlin', 'London'];
        $scope.quiz.inputs = [];
        $scope.quiz.continue = false;
        $scope.quiz.mistake = false;

        $scope.quiz.newPage = function(page){
            $window.location.assign("/quiz/user/" +  oid + "#/" + page);
            $scope.quiz.continue = false;
            $scope.quiz.mistake = false;


        }
        $scope.quiz.begin = function() {
            $scope.quiz.newPage('0');
        }

        $scope.quiz.validate = function(question) {
            if ($scope.quiz.answers[question] === $scope.quiz.inputs[question]) {
                if (!$scope.quiz.mistake) {
                    dataModel.correct++;
                }
                $scope.quiz.newPage(question + 1);
            }
            else {
                $scope.quiz.mistake = true;    
            }
        }

        $scope.quiz.numCorrect = function() {
            return dataModel.correct;
        }

        $scope.quiz.pass = function() {
            return dataModel.correct >= 2;
        }

        $scope.quiz.finish = function() {
            $window.location.assign("/instructionsemployer?oid=" + oid);
        }

        $scope.quiz.timeUp = false;
        $scope.quiz.counter = 30;

        var stop;
        $scope.quiz.countdown = function(){
            if ( angular.isDefined(stop) ) return;

            stop = $interval(function() {
                if ($scope.quiz.counter > 0) {
                    $scope.quiz.counter--;
                } else {
                    $scope.quiz.timerStop();
                }
            }, 1000); 
        };
        $scope.quiz.countdown();

        $scope.quiz.timerStop = function() {
            $scope.quiz.timeUp = true;
            if (angular.isDefined(stop)) {
                $interval.cancel(stop);
                stop = undefined;
            }
        };

        $scope.$on('$destroy', function() {
          // Make sure that the interval is destroyed too
          $scope.quiz.timerStop();
        });
    }]);

