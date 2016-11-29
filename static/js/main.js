'use strict';

var mainApp = angular.module('mainApp', ['ngResource']);


mainApp.service("userInfo", function() {
    this.name = "default";
})

mainApp.controller('MainController', ['$scope', '$resource', 'userInfo',
    function ($scope, $resource, userInfo) {
        $scope.main = {};
        $scope.main.user = {};
        $scope.main.user.name = "default";


        $scope.main.getName = function() {
            return userInfo.name;
        }
        $scope.main.register = function() {
            userInfo.name = $scope.main.user.name
            var Register = $resource('/api/player/register');
            Register.save(userInfo);
        }

    }]);

