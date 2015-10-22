function form_to_query(form, command)
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
    query = form_to_query(form, command);
    xhttp.open("GET", query, true);
    xhttp.send();
}
