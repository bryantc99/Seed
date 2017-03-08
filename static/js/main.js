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

mainApp.controller('MainController', ['$scope', '$resource', 'userInfo',
    function ($scope, $resource, userInfo) {
        $scope.main = {};
        $scope.main.user = {};
        $scope.main.user.name = "default";


        $scope.main.getName = function() {
            return userInfo.name;
        }


    }]);

