var match_form_timers = [null, null, null, null];

function universal_json_to_form(form, data)
{
    var i, p;
    for (i = 0; i < form.length; i++) {
        p = form[i].name;
        if (data.hasOwnProperty(p))
            form[i].value = data[p];
    }
}

function player_json_to_form(form, data)
{
    if (typeof form.active !== 'undefined') {
        if (data.hasOwnProperty("active")) {
            if (data["active"]) {
                form.active[1].selected = true;
            } else {
                form.active[2].selected = true;
            }
        }
    }
}

function universal_form_to_password(form)
{
    var i;

    for (i = 0; i < form.length; i++)
        if (form[i].name && form[i].name == 'password')
            return form[i].value;
}

function universal_form_to_query(form, command)
{
    var i;
    var first_arg = true;
    var q = form.action;

    q+= command;
    for (i = 0; i < form.length; i++)
        if (form[i].name) {
            if (form[i].name != 'password' && (form[i].value || form[i].type == "checkbox")) {
                if (first_arg) {
                    q += "?";
                    first_arg = false;
                } else
                    q += "&";
                if (form[i].type == "checkbox")
                    q += form[i].name + "=" + form[i].checked;
                else
                    q += form[i].name + "=" + encodeURIComponent(form[i].value);
            }
        }
    return q;
}

function reset_checkbox(id)
{
    checkbox = document.getElementById(id);
    if (checkbox)
        checkbox.checked = false;
}

function match_form_to_query(form, command)
{
    var q = form.action;
    var challenger = "nobody";
    var opponent = "nobody";
    var i;

    q+= command;

    // determine the challenger
    if (document.getElementById('player_1_challenger').checked) {
        challenger = "player_1";
        opponent = "player_2";
    }
    if (document.getElementById('player_2_challenger').checked) {
        if (challenger == "player_1") {
            alert("Huh? Two challengers?");
            return null;
        }
        challenger = "player_2";
        opponent = "player_1";
    }
    if (challenger == "nobody") {
        alert("No challengers ... please!");
        return null;
    }
    console.log("challenger is " + challenger);
    console.log("opponent is " + opponent);

    challenger_id = document.getElementById(challenger + '_id').value;
    opponent_id = document.getElementById(opponent + '_id').value;

    q += '?challenger=' + challenger_id + '&opponent=' + opponent_id;

    // extract the match score, HTML IDs follow the pattern set_N_player_M_score,
    // which we synthesise from challenger/opponent strings (generated above)
    for (i = 1; i < 4; i++) {
        cgames = document.getElementById('set_' + i + '_' + challenger + '_score').value;
        ogames = document.getElementById('set_' + i + '_' + opponent + '_score').value;
        console.log("set " + i + " score is: " + cgames + ":" + ogames);
        if (cgames && ogames)
        q += '&cgames=' + cgames + '&ogames=' + ogames;
    }
    match_date = document.getElementById('match_date_3').value + '-' +
        document.getElementById('match_date_1').value + '-' +
        document.getElementById('match_date_2').value;
    if (document.getElementById('match_outcome_2').checked)
        q += '&retired=true';
    if (document.getElementById('match_outcome_3').checked)
        q+= '&forfeited=true';
    q += '&date=' + match_date;

    console.log("query is " + q);
    return q;
}

function season_form_to_query(form, command)
{
    var q = form.action;

    q+= command;
    title = document.getElementById('title').value;
    q+= '?title=' + title;

    start_date = document.getElementById('start_date_3').value + '-' +
        document.getElementById('start_date_1').value + '-' +
        document.getElementById('start_date_2').value;
    q += '&start_date=' + start_date;

    end_date = document.getElementById('end_date_3').value + '-' +
        document.getElementById('end_date_1').value + '-' +
        document.getElementById('end_date_2').value;
    q += '&end_date=' + end_date;

    return q;
}

function token_form_to_query(form, command)
{
    var q = form.action;

    q+= command;
    q+= '?token_type=report_and_roster';

    since_date = document.getElementById('since_date_3').value + '-' +
        document.getElementById('since_date_1').value + '-' +
        document.getElementById('since_date_2').value;
    q += '&since_date=' + since_date;

    expires_date = document.getElementById('expires_date_3').value + '-' +
        document.getElementById('expires_date_1').value + '-' +
        document.getElementById('expires_date_2').value;
    q += '&expires_date=' + expires_date;

    return q;
}

function clear_list(list_name)
{
    var clear_me = document.getElementById(list_name);
    clear_me.innerHTML = "";
}

function clear_form(form_name)
{
    form = document.getElementById(form_name);
    form.reset();
    return form;
}

function clear_form_and_list(form_name, list_name)
{
    clear_list(list_name);
    clear_form(form_name);
}

function populate_player_form_with_data(data)
{
    form = clear_form("player_form");
    universal_json_to_form(form, data);
    player_json_to_form(form, data);
}

function populate_player_list(data)
{
    var i, s;
    var player_list = document.getElementById("player_list");
    player_list.innerHTML = "<h3>Multiple Matches</h3><ul>"
    for (i = 0; i < data.length; i++) {
        s = "<li><div id=" + data[i].player_id + ">";
        s +=  "" + data[i].player_id + ": " + data[i].first_name + " " + data[i].last_name;
        s += "&nbsp&nbsp&nbsp";
        s += "<image src='pencil_edit.png' height='16' width='16'";
        s += "title='Edit " + data[i].first_name + " " + data[i].last_name;
        s += "' alt='edit' onclick='"
        s += "populate_player_form_with_data(" + JSON.stringify(data[i]) + ")'>";
        s += "</div></li>";
        player_list.innerHTML += s;
    }
    player_list.innerHTML += '</ul><div class="form_description"><p></p></div>';
}

function get_logged_in_player_data()
{
    var xhttp = new XMLHttpRequest();
    var query, form;

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_player_form_response("get_player", JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById("player_form");
    query = form.action + "get_player?player_id=-1";
    xhttp.open("GET", query, true);
    xhttp.send();

}

function process_player_form_response(command, response)
{
    var form_name = "player_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        switch (command) {
        case "add_player":
            form.reset();
            clear_list("player_list");
            alert("player id is " + response.player_id + ".");
            break;
        case "update_player":
            form.reset();
            // no break, intentionally!
        case "update_player_restricted":
            alert("player with id " + response.player_id + " updated.");
            break;
        case "get_player":
            var data = response.entries;
            form.reset();
            if (data.length == 0)
                alert("no players found");
            else if (data.length == 1) {
                clear_list("player_list");
                universal_json_to_form(form, data[0]);
                player_json_to_form(form, data[0]);
            } else {
                populate_player_list(data);
            }
            break;
        case "del_player":
            form.reset();
            clear_list("player_list");
            alert("player with id " + response.player_id + " deleted.");
            break;
        default:
            form.reset();
            alert("should not happen, bug?");
        }
    } else {
        alert("Error: " + response.reason);
    }
}

function populate_player_box(data, form, box, field)
{
    var player;
    if (data.result == "success") {
        if (data.entries.length == 1) {
            player = data.entries[0];
            if (field == 'id')
                form[box].value = player.player_id;
            else
                form[box].value = player.last_name;
        } else
            form[box].value = "";
    } else
        form[box].value = "";
}

function do_box_completion(player_last_name_box, player_id_box, timer_index, field)
{
    var q, form;
    var xhttp = new XMLHttpRequest();
    var form_name = "match_form";

    clearTimeout(match_form_timers[timer_index]);
    match_form_timers[timer_index] = null;
    if (field == "id")
        player_box = player_id_box;
    else
        player_box = player_last_name_box;
    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                populate_player_box(JSON.parse(xhttp.responseText), form, player_box, field);
            }
        }
    }
    form = document.getElementById(form_name);
    q = form.action;
    if (field == "id") {
        q += "get_player?last_name=";
        q += document.getElementById(player_last_name_box).value;
    } else {
        q += "get_player?player_id=";
        q += document.getElementById(player_id_box).value;
    }
    xhttp.open("GET", q, true);
    xhttp.send();
}

function player_box_completion(player_last_name_box, player_id_box, timer_index, field)
{
    var typing_delay = 1000;

    // user has typed something in the form box, use timer that we keep
    // rearming for as long as user is typing; one second after user
    // has stopped typing in that box, fire the timer and do the database lookup
    if (match_form_timers[timer_index])
        clearTimeout(match_form_timers[timer_index]);
    match_form_timers[timer_index] = setTimeout(
        function () {
            do_box_completion(player_last_name_box, player_id_box, timer_index, field);
        },
        typing_delay);
}

function populate_match_list(data)
{
    var s;
    var match_list;
    var inner_match_list;

    match_list = document.getElementById("match_list");
    if (match_list.innerHTML == "") {
        match_list.innerHTML = "<h3>Recent Matches</h3><ul>";
        match_list.innerHTML += '<div id="inner_match_list"></div>';
        match_list.innerHTML += '</ul><div class="form_description"><p></p></div>';
    }
    s = "<li>Match " + data.match_id + ": ";
    s += data.date + ", ";
    s += "" + data.winner_last_name + " def. " + data.loser_last_name;    
    s += "</li>";
    inner_match_list = document.getElementById("inner_match_list");
    inner_match_list.innerHTML += s;
}

function process_match_form_response(command, response)
{
    var form_name = "match_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset();
        populate_match_list(response);
    } else {
        alert("Error: " + response.reason);
    }
}

function process_season_form_response(command, response)
{
    var form_name = "season_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset();
        alert("New season created, ID=" + response.season_id);
    } else {
        alert("Error: " + response.reason);
    }
}

function process_token_form_response(command, action, response)
{
    var form_name = "token_form";
    var token_list = document.getElementById("token_list");

    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset();
        token_url = action + "report?token=" + response.token;
        token_list.innerHTML = "<h3>Token URL is:</h3><ul>";
        token_list.innerHTML += token_url + "</div></li><li></li>";
    } else {
        alert("Error: " + response.reason);
    }
}

function populate_account_form_with_data(data)
{
    form = clear_form("account_form");
    universal_json_to_form(form, data);
}

function populate_account_list(data)
{
    var i, s;
    var account_list = document.getElementById("account_list");
    account_list.innerHTML = "<h3>Admin Accounts in the System</h3><ul>"
    for (i = 0; i < data.length; i++) {
        s = "<li><div id=" + data[i].account_id + ">";
        s +=  "" + data[i].username;
        s += "&nbsp&nbsp&nbsp";
        s += "<image src='pencil_edit.png' height='16' width='16'";
        s += "title='Edit " + data[i].username;
        s += "' alt='edit' onclick='"
        s += "populate_account_form_with_data(" + JSON.stringify(data[i]) + ")'>";
        s += "</div></li>";
        account_list.innerHTML += s;
    }
    account_list.innerHTML += '</ul><div class="form_description"><p></p></div>';
}

function process_account_form_response(command, response)
{
    var form_name = "account_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        switch (command) {
        case "add_account":
            clear_form_and_list("account_form", "account_list");
            alert("account id is " + response.account_id + ".");
            break;
        case "update_account":
            form.reset();
            alert("account with id " + response.account_id + " updated.");
            break;
        case "list_account":
            form.reset();
            var data = response.entries;
            if (data.length == 0)
                alert("no accounts found");
            else
                populate_account_list(data);
            break;
        case "del_account":
            form.reset();
            clear_list("account_list");
            alert("account with id " + response.account_id + " deleted.");
            break;
        default:
            alert("should not happen, bug?");
        }
    } else {
        alert("Error: " + response.reason);
    }
}

function process_submit_error(err)
{
    alert("oops, something failed (error=" + err + ")");
}

function add_player_pre_check()
{
    var q, form;
    var xhttp = new XMLHttpRequest();
    var form_name = "player_form";

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                check_existing_player(JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById(form_name);
    q = form.action;
    q += "get_player?";
    q += "first_name=" + form.first_name.value;
    q += "&last_name=" + form.last_name.value;
    xhttp.open("GET", q, true);
    xhttp.send();
}

function check_existing_player(response)
{
    var data = response.entries;
    var cstr;
    if (response.result == "success") {
        if (data.length == 0) {
            process_player_form("add_player");
        } else {
            if (data.length == 1)
                cstr = " player ";
            else
                cstr = " players ";
            if (confirm("Found " + data.length + cstr + "with the same name! Really add?"))
                process_player_form("add_player");
        }
    } else {
        alert("oops:" + response.reason)
    }
}

function process_player_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "player_form";
    var password;

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_player_form_response(command, JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById(form_name);
    if (command == "add_player")
        if (form.player_id.value) {
            alert("ID for a new player will be automatically assigned, please leave it blank.");
            return;
        }
    if (command == "del_player") {
        if (!confirm("Are you sure you want to delete the player?\nUsually, just inactivating the player is good enough."))
            return;
    }
    if (command == "update_player_restricted")
        query = universal_form_to_query(form, "update_player");
    else
        query = universal_form_to_query(form, command);
    password = universal_form_to_password(form);
    xhttp.open("POST", query, true);
    xhttp.send(password);
}

function process_match_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "match_form";

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_match_form_response(command, JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById(form_name);
    query = match_form_to_query(form, command);
    if (query) {
        xhttp.open("GET", query, true);
        xhttp.send();
    }
}

function process_season_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "season_form";

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_season_form_response(command, JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById(form_name);
    query = season_form_to_query(form, command);
    if (query) {
        xhttp.open("GET", query, true);
        xhttp.send();
    }
}

function process_token_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "token_form";

    form = document.getElementById(form_name);
    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_token_form_response(command, form.action, JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    query = token_form_to_query(form, command);
    if (query) {
        xhttp.open("GET", query, true);
        xhttp.send();
    }
}

function check_season_form(command)
{
    if (confirm("This will archive the ladder and reset the scores. Proceed?"))
        process_season_form(command);
}

function process_account_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "account_form";
    var password;

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_account_form_response(command, JSON.parse(xhttp.responseText));
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    if (command == "del_account") {
        if (!confirm("You are about to delete an admin account.\nPlease confirm that you know what you are doing."))
            return;
    }
    form = document.getElementById(form_name);
    if (command == "list_account") {
        // list_account is special: implemented through get_account
        query="get_account";
        xhttp.open("GET", query, true);
        xhttp.send();
    } else {
        query = universal_form_to_query(form, command);
        password = universal_form_to_password(form);
        xhttp.open("POST", query, true);
        xhttp.send(password);
    }
}
