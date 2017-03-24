$(document).ready(function() {
  $('.grouping').addClass('container');
  $('.grouping .form-group').addClass('col');
  $('.grouping').append('<div class="row"></div>');
  $('.grouping .row').append($('.grouping .col'));
  $('.grouping .form-group').removeClass('form-group');
 
});
