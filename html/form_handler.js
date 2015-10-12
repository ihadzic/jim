function form_to_query(form)
{
    var i;
    var q = form.action;

    for (i = 0; i < form.length; i++)
        if (form[i].value)
            q += "&" + form[i].name + "=" + form[i].value;
    return q;
}

function enter_player()
{
    var form, query;

    form = document.getElementById('form_enter_player');
    query = form_to_query(form);
    // TODO: send the query
    alert(query);
    // prevent default form submission (we do everything from this script)
    return false;
}
