function form_to_query(form, command)
{
    var i;
    var first_arg = true;
    var q = form.action;

    q+= command;
    for (i = 0; i < form.length; i++)
        if (form[i].value) {
            if (first_arg) {
                q += "?";
                first_arg = false;
            } else
                q += "&";
            q += form[i].name + "=" + form[i].value;
        }
    return q;
}

function process_player_form_response(command, response)
{
    var form_name = "player_form";
    if (response.result == "success") {
	alert("player id is " + response.player_id);
        form = document.getElementById(form_name);
        form.reset();
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
    query = form_to_query(form, command);
    xhttp.open("GET", query, true);
    xhttp.send();
}
