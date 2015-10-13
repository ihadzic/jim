function form_to_query(form)
{
    var i;
    var first_arg = true;
    var q = form.action;

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

function process_submit_response(response)
{
    alert("got this: " + response);
}

function enter_player()
{
    var form, query;
    var xhttp = new XMLHttpRequest();

    xhttp.onreadystatechange = function() {
        if (xhttp.readyState == 4 && xhttp.status == 200)
            process_submit_response(xhttp.responseText);
    }
    form = document.getElementById('form_enter_player');
    query = form_to_query(form);
    xhttp.open("GET", query, true);
    xhttp.send();
    // prevent default form submission (we do everything from this script)
    return false;
}
