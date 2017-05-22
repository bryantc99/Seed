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
    this.us_ids = ['us1', 'us2', 'us3', 'us4']
    this.india_ids = ['india1', 'india2']
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

        $scope.main.counter = 60;
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
                return false;
            }
            else {
                return true;
                userInfo.name = $scope.main.user.name;
                $http({
                    method: 'POST',
                    url: '/about',
                    data: {name: $scope.main.user.name},
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    transformRequest: function(obj) {
                        var str = [];
                        for(var p in obj)
                        str.push(encodeURIComponent(p) + "=" + encodeURIComponent(obj[p]));
                        return str.join("&");
                    },

                }).then(function successCallback(response) {
                }, function errorCallback(response) {
                });
            }
        }

        $scope.validateForm = function(e) {
            console.log(e);
            var x = document.forms["messageform"]["name"].value;
            if (userInfo.us_ids.indexOf(x) == -1 && userInfo.india_ids.indexOf(x) == -1) {
                e.preventDefault();
                alert("That is an invalid or duplicate ID.");
                return false;

            }            
        }

        $scope.main.reset = function() {
            $scope.main.counter = 60;
        }

        $scope.$on('$destroy', function() {
          // Make sure that the interval is destroyed too
          $scope.main.timerStop();
        });


    }]);

