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

function process_submit_response(ok_string, response, form_name)
{
    if (response.result == "success") {
        form = document.getElementById(form_name);
        form.reset()
    } else {
        alert("Error: " + response.reason);
    }
}

function process_submit_error(err)
{
    alert("oops, something failed (error=" + err + ")");
}

function process_submit_form(command, ok_string, form_name)
{
    var form, query;
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4) {
            if (xhttp.status == 200) {
                process_submit_response(ok_string, JSON.parse(xhttp.responseText), form_name);
            } else {
                process_submit_error(xhttp.status);
            }
        }
    }
    form = document.getElementById(form_name);
    query = form_to_query(form, command);
    xhttp.open("GET", query, true);
    xhttp.send();
    // prevent default form submission (we do everything from this script)
    return false;
}
