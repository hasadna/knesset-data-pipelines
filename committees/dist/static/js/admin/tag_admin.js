tag_admin = {

    _set_action: function(html, secondary_html, msg) {
        $('.tag_synonym_action').html(html);
        $('.tag_synonym_secondary_action').html(secondary_html);
        $('.tag_synonym_msg').html(msg);
    },

    _waitFor$: function(callback) {
        if ($) {
            callback();
        } else {
            setTimeout(function() {
                tag_admin._waitFor$(callback);
            }, 5);
        }
    },

    init: function() {
        document.write('<script type="text/javascript" src="http://code.jquery.com/jquery-1.11.0.min.js"></script>');
        tag_admin._waitFor$(function() {
            $(function() {
                if (window.sessionStorage['choose_synonym_for']) {
                    tag_admin._set_action('( סימון כתג נרדף )', ' | ( ביטול )', ' -- תגית אב: '+window.sessionStorage['parent_tag_name']+' -- ');
                }
            });
        });
    },

    tag_synonym_click: function(tag_id, tag_name) {
        if (window.sessionStorage['choose_synonym_for']) {
            var parent_tag = window.sessionStorage['choose_synonym_for'];
            var synonym_tag = tag_id;
            this._set_action('( נא להמתין ... )', '', '');
            $.get('/add_tag_synonym/'+parent_tag+'/'+synonym_tag+'/', function() {
                //window.sessionStorage.clear();
                //tag_admin._set_action('( add synonym )', '');
                tag_admin._set_action('( סימון כתג נרדף )', ' | ( ביטול )', ' -- תגית אב: '+window.sessionStorage['parent_tag_name']+' -- בוצע -- ');
            });
        } else {
            window.sessionStorage['choose_synonym_for'] = tag_id;
            window.sessionStorage['parent_tag_name'] = tag_name;
            this._set_action('( סימון כתג נרדף )', ' | ( ביטול )', ' -- תגית אב: '+window.sessionStorage['parent_tag_name']+' -- ');
        }
    },

    tag_synonym_secondary_click: function(tag_id) {
        window.sessionStorage.clear();
        tag_admin._set_action('( הוספת תג נרדף )', '', '');
    }

};

tag_admin.init();
