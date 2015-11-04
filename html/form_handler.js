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

function match_form_to_query(form, command)
{
    var q = form.action;
    var challenger = "nobody";
    var opponent = "nobody";
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

    // extract the match score, HTML IDs follow the pattern set_N_player_M_score,
    // which we synthesise from challenger/opponent strings (generated above)
    cgames1 = document.getElementById('set_1_' + challenger + '_score').value;
    cgames2 = document.getElementById('set_2_' + challenger + '_score').value;
    cgames3 = document.getElementById('set_3_' + challenger + '_score').value;
    ogames1 = document.getElementById('set_1_' + opponent + '_score').value;
    ogames2 = document.getElementById('set_2_' + opponent + '_score').value;
    ogames3 = document.getElementById('set_3_' + opponent + '_score').value;
    console.log("set 1 score is: " + cgames1 + ":" + ogames1);
    console.log("set 2 score is: " + cgames2 + ":" + ogames2);
    console.log("set 3 score is: " + cgames3 + ":" + ogames3);

    q += '?challenger=' + challenger_id;
    q += '&opponent=' + opponent_id;
    if (cgames1 && ogames1)
        q += '&cgames=' + cgames1 + '&ogames=' + ogames1;
    if (cgames2 && ogames2)
        q += '&cgames=' + cgames2 + '&ogames=' + ogames2;
    if (cgames3 && ogames3)
        q += '&cgames=' + cgames3 + '&ogames=' + ogames3;

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
            // TODO: fill up the form or construct the list of players for multiple matches
            alert("got this: " + JSON.stringify(response));
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
