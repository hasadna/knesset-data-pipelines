function showHelpText(elt) {
    var helptext = $(elt).data('helptext');
    var moreinfo = $(elt).data('moreinfo');
    if (moreinfo) {
        helptext += '<p><a href="'+moreinfo+'">למידע נוסף</a></p>'
    }
    $('#okhelptextscontainer .modal-body p').html(helptext);
    $('#okhelptextscontainer').modal();
}
$(function() {
   $('body').append('' +
        '<div id="okhelptextscontainer" class="modal hide fade" tabindex="-1" role="dialog" aria-hidden="true">' +
            // '<div class="modal-header">' +
            //     '<button type="button" class="close" data-dismiss="modal" aria-hidden="true">×</button>' +
            //     '<h3>Modal header</h3>' +
            // '</div>' +
            '<div class="modal-body">' +
                '<p></p>' +
            '</div>' +
            '<div class="modal-footer">' +
                '<button class="btn" data-dismiss="modal" aria-hidden="true">סגור</button>' +
            '</div>' +
        '</div>' +
   '');
});