function universal_json_to_form(form, data)
{
    var i, p;
    for (i = 0; i < form.length; i++) {
        p = form[i].name;
        if (data.hasOwnProperty(p))
            form[i].value = data[p];
    }
}

function universal_form_to_query(form, command)
{
    var i;
    var first_arg = true;
    var q = form.action;

    q+= command;
    for (i = 0; i < form.length; i++)
        if (form[i].name) {
            if (form[i].value || form[i].type == "checkbox") {
                if (first_arg) {
                    q += "?";
                    first_arg = false;
                } else
                    q += "&";
                if (form[i].type == "checkbox")
                    q += form[i].name + "=" + form[i].checked;
                else
                    q += form[i].name + "=" + form[i].value;
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

function process_player_form_response(command, response)
{
    var form_name = "player_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset();
        switch (command) {
        case "add_player":
            alert("player id is " + response.player_id + ".");
            break;
        case "update_player":
            alert("player with id " + response.player_id + " updated.");
            break;
        case "get_player":
            if (response.result == "success") {
                var data = response.entries;
                if (data.length == 0)
                    alert("no players found");
                else if (data.length == 1)
                    universal_json_to_form(form, data[0]);
                else
                    alert("multiple players matched, not implemented yet");
            } else {
                alert("oops:" + response.reason)
            }
            break;
        case "del_player":
            alert("player with id " + response.player_id + " deleted.");
            break;
        default:
            alert("should not happen, bug?");
        }
    } else {
        alert("Error: " + response.reason);
    }
}

function process_match_form_response(command, response)
{
    var form_name = "match_form";
    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset();
        alert("TODO: process successful match submission");
    } else {
        alert("Error: " + response.reason);
    }
}

function process_submit_error(err)
{
    alert("oops, something failed (error=" + err + ")");
}

function process_player_form(command)
{
    var form, query;
    var xhttp = new XMLHttpRequest();
    var form_name = "player_form";

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
    query = universal_form_to_query(form, command);
    xhttp.open("GET", query, true);
    xhttp.send();
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
