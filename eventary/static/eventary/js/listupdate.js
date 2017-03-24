$(document).ready(function() {
  $('.toggle_selection input[type=checkbox]').change(function (eventObject) {
    $('input[name=pk]', $(this).closest('form')).prop('checked', this.checked);
  });
});
