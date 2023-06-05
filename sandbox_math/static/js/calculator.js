function SetCalculatorHeight() {
  let newHeight = $('#algebra').height() - 38;
  $('#calculatorDialog').css('height', newHeight + 'px');
  let simplebarWrapper = $('#calculatorDialog .simplebar-content-wrapper');
  simplebarWrapper.animate(
    { scrollTop: simplebarWrapper.prop('scrollHeight') },
    'slow',
  );
}
