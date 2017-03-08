$( document ).ready(function() {
  /**
   * This hides the recurrence form and displays it only if the recurrence
   * option is selected
   */

  // initial setting
  if ($('#id_recurring')[0].checked) {
    $('.recurrenceform').show();
  } else {
    $('.recurrenceform').hide();
  }

  // toggle with the checkbox
  $('#id_recurring').change(function(eventObject) {
    if (this.checked) {
      $('.recurrenceform').show();
    } else {
      $('.recurrenceform').hide();
    }
  })
});
