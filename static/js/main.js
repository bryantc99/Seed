'use strict';

var mainApp = angular.module('mainApp', ['ngResource']);

function getUrlVars() {
    var vars = {}; 
    window.location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) { vars[key] = value; }); 
    return vars;
}

var params = getUrlVars();

if(document.getElementById("tutorialEntry")) {
    document.getElementById("tutorialEntry").action = "tutorial1/user/" + params['oid'];
}

if(document.getElementById("tutorial2Entry")) {
    document.getElementById("tutorial2Entry").action = "tutorial2/user/" + params['oid'];
}


mainApp.service("userInfo", function() {
    this.name = "default";
})

mainApp.controller('MainController', ['$scope', '$resource', '$interval', '$http', 'userInfo', 
    function ($scope, $resource, $interval, $http, userInfo) {
        $scope.main = {};
        $scope.main.user = {};
        $scope.main.user.name = "default";
        $scope.main.timeUp = false;
        $scope.main.wrongId = false;

        $scope.main.getName = function() {
            return userInfo.name;
        }

        $scope.main.counter = 10;
        var stop;
        $scope.main.countdown = function(){
            if ( angular.isDefined(stop) ) return;

            stop = $interval(function() {
                if ($scope.main.counter > 0) {
                    $scope.main.counter--;
                } else {
                    $scope.main.timerStop();
                }
            }, 1000); 
        };
        $scope.main.countdown();

        $scope.main.timerStop = function() {
            $scope.main.timeUp = true;
            if (angular.isDefined(stop)) {
                $interval.cancel(stop);
                stop = undefined;
            }
        };

        $scope.main.validate = function() {
            console.log("validate");
            if ($scope.main.user.name != "Gerald") {
                $scope.main.wrongId = true;
            }
            else {
                userInfo.name = $scope.main.user.name;
                $http({
                    method: 'POST',
                    url: '/about',
                    params: {name: $scope.main.user.name}
                }).then(function successCallback(response) {
                }, function errorCallback(response) {
                });
            }
        }

        $scope.$on('$destroy', function() {
          // Make sure that the interval is destroyed too
          $scope.main.timerStop();
        });


    }]);

