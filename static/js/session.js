'use strict';

    // variables
var countdown = null,
	heartbeat = null,
	countdownOpen = false,
	game = "",
	subject = null;


var WAIT_MSG = 99,
    ENTRY_MSG = 100,
    ACTIVATE_MSG = 101,
    DEACTIVATE_MSG = 102,
    FULL_MSG = 103,
    CLOSE_MSG = 104,
    SESSION_MSG = 105,
    HEARTBEAT_MSG = 106,
    NO_CONFIG_MSG = 110,
    DUPLICATE_MSG = 111;

var HEARTBEAT_INTERVAL = 4000,
	HEARTBEAT = "h";

var conn = null,
	admitted = false,
	full = false,
	error = false,
	retries = 0,
	retry_id = null,
	timeout = null;


function checkin() {
    console.log("check in");
}

function enter() {
    // send ENTRY_MSG
    var entry_msg = JSON.stringify({"type": ENTRY_MSG});
    conn.send(entry_msg);

    return false;
}

function stopHeartbeat() {
    if (heartbeat !== null) {
        clearTimeout(heartbeat);
        heartbeat = null;
    }
}

function getUrlVars() {
    var vars = {}; 
    window.location.search.replace(/[?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) { vars[key] = value; }); 
    return vars;
}


function connect() {
    disconnect();
    var params = getUrlVars();

    var protocols = ["websocket", "xdr-streaming", "xhr-streaming", "xdr-polling", "xhr-polling", "iframe-eventsource"];
    var options = {protocols_whitelist: protocols, debug: true, jsessionid: false};
    conn = new SockJS("https://intense-sands-23697.herokuapp.com/sockjs/session", null, options);
    console.log("Client - connecting...");

    
    conn.onopen = function() {
        console.log("Client - connected");
        console.log("Client - protocol used: " + conn.protocol);
        // send WAIT_MSG
        var wait_msg = JSON.stringify({"type": WAIT_MSG});
        conn.send(wait_msg);
        console.log("Client - WAIT_MSG sent");
    };
    

    conn.onclose = function() {
        console.log("Client - disconnected");
        // cancel HEARTBEAT
        stopHeartbeat();
        conn = null;

        // try re-connect in case of unintended disconnection
        // 3 times only
        if (!full && !admitted && !error && retries < 3) {
            if (retry_id !== null) {
                clearTimeout(retry_id);
                retry_id = null;
            }
            // try auto-re-connect
            retries++;
            console.log("Client - re-connecting " + retries + "...");
            retry_id = setTimeout(connect, Math.pow(2, retries) * 1000);
        }
        else if (retries >= 3) {
            console.log("Connection Problem");
        }
    };

    conn.onmessage = function(e) {
        var msg = JSON.parse(e.data);
        var type = parseInt(msg.type);

        if (type === ACTIVATE_MSG) {
            console.log("Client - activated");
            //document.getElementById("oid").value = params['oid'];
            document.getElementById("gameEntry").action = "game/user/" + params['oid'];
            document.getElementById("proceed").style.display = "block";
        }
        else if (type === DEACTIVATE_MSG) {
            console.log("Client - deactivated");
            proceed.css("display", "none");
            proceed.off("click").one("click", function(e) {
                enter();
            });
        }
        else if (type === FULL_MSG) {
            console.log("Client - session full");
            proceed.css("display", "none");
            fullExp.show();
            full = true;
            stopHeartbeat();
            disconnect();
        }
        else if (type === SESSION_MSG) {
            console.log("Client - joining in session...");

            $.ajax({
                url: msg.url,
                type: "POST",
                data: {"session": msg.session_id},
                dataType: "json",
                tryCount: 0,
                retryLimit: 3,
                // callback handler that will be called on success
                success: function(response, textStatus, jqXHR) {
                    console.log(response["ad"]);
                    if (response["ad"] === true) {
                        admitted = true;
                        stopHeartbeat();
                        disconnect();
                        window.location.replace(response["url"]);
                    }
                    else {
                        error = true;
                        stopHeartbeat();
                        disconnect();
                        window.location.replace("https://www.playmymodel.com/game/denied");
                    }
                },
                // callback handler that will be called on error
                error: function(jqXHR, textStatus, errorThrown) {
                    if (textStatus === "timeout" || textStatus === "error" || textStatus === "parsererror") {
                        this.tryCount++;
                        if (this.tryCount < this.retryLimit) {
                            //try again
                            if (timeout !== null) {
                                window.clearTimeout(timeout);
                                timeout = null;
                            }
                            var reqOptions = this;
                            timeout = window.setTimeout(function() {
                                $.ajax(reqOptions);
                            }, 3000);
                        } else {
                            console.log("Connection Problem");
                        }
                    }
                },
                // callback handler that will be called on completion
                // which means, either on success or error
                complete: function() {
                    
                }
            });
        }
        else if (type === NO_CONFIG_MSG) {
            error = true;
            stopHeartbeat();
            disconnect();
            console.log("Inactive Experiment");
        }
        else if (type === CLOSE_MSG) {
            full = true;
            stopHeartbeat();
            disconnect();
            window.location.replace("https://loc/game/closed");
        }
        else if (type === DUPLICATE_MSG) {
            error = true;
            stopHeartbeat();
            disconnect();
            console.log("Multiple Participations");
        }
        else if (type === HEARTBEAT_MSG) {
            // enable heartbeats here
            console.log("Client - start heartbeats");
            startHeartbeat();
        }
        else {
            error = true;
            stopHeartbeat();
            disconnect();
            console.log("Client - wtf just happened?!");
        }
    };
}

function disconnect() {
    if (conn !== null) {
        console.log("Client - disconnecting...");
        conn.close();
        conn = null;
        console.log("Client - disconnected");
    }
}

function credential() {

    $.ajax({
        url: 'http://localhost:5000/api/player/register',
        type: "GET",
        // callback handler that will be called on success
        success: function(response, textStatus, jqXHR) {
            alert("Success");
            window.console && console.log(response["ps"]);
            if (response["ps"] === true) {
                game = response["gm"];
                subject = response["sb"];
                connect();
            }
            else if (response["ps"] === false) {
                error = true;
                stopHeartbeat();
                disconnect();
                window.location.replace("https://localhost:5000/game/denied");
            }
        },
        // callback handler that will be called on error
        error: function(jqXHR, textStatus, errorThrown) {
            alert("Fail");
            if (textStatus === "timeout" || textStatus === "error" || textStatus === "parsererror") {
                this.tryCount++;
                if (this.tryCount < this.retryLimit) {
                    //try again
                    if (timeout !== null) {
                        window.clearTimeout(timeout);
                        timeout = null;
                    }
                    var reqOptions = this;
                    timeout = window.setTimeout(function() {
                        $.ajax(reqOptions);
                    }, 3000);
                } else {
                    console.log("Connection Problem");
                }
            }
        },
        // callback handler that will be called on completion
        // which means, either on success or error
        complete: function() {
            
        }
    });
}

connect();
