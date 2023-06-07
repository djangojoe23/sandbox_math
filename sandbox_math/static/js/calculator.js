function InitializeCalculator() {
  let calculatorField = MQ.MathField($('#calculatorInput')[0]);

  $('#calculatorDialog .simplebar-content').addClass('px-2');

  $('#calculatorSubmit').click(function () {
    if (calculatorField.latex().length) {
      SubmitUserMessage();
      calculatorField.latex('');
    }
  });
  let calculatorInputTextArea = $('#calculatorInput textarea');
  calculatorInputTextArea.focus(function () {
    $('#calculatorInputBorder').css({
      'border-color': 'var(--ar-gray-700)',
      outline: '0',
      'box-shadow': 'unset',
    });
  });
  calculatorInputTextArea.blur(function () {
    $('#calculatorInputBorder').css({
      'border-color': '',
      outline: '',
      'box-shadow': '',
    });
  });
  let timeout = null;
  calculatorField.config({
    supSubsRequireOperand: true,
    restrictMismatchedBrackets: true,
    autoOperatorNames: 'randomstringnoonewillevertypeinhopefully',
    autoCommands: 'randomstringnoonewillevertypeinhopefully',
    maxDepth: 1,
    handlers: {
      edit: function () {
        if (timeout != null) {
          clearTimeout(timeout);
        }
        timeout = setTimeout(function () {
          if (
            calculatorField
              .latex()
              .includes('randomstringnoonewillevertypeinhopefully')
          ) {
          } else {
            //do i want to do something while user is typing a message?
            let tabParent = $('.tab-content').parent();
            let newHeight = tabParent.height();
            tabParent.css('min-height', newHeight + 'px');
          }
        }, 100);
      },
      enter: function () {
        if (calculatorField.latex().length) {
          SubmitUserMessage();
          calculatorField.latex('');
        }
      },
    },
  });
}

function SubmitUserMessage() {
  let calcInputObj = MQ.MathField($('#calculatorInput')[0]);
  $('#calculatorSubmit').prop('disabled', 'disabled');
  calcInputObj.config({
    handlers: {
      enter: function () {},
    },
  });

  //Messages from the user are always assumed to be all latex
  let userMessage = calcInputObj.latex();

  $('#calculatorDialog .simplebar-content').append(
    "<div class='ms-auto mb-3 w-75 user-message'>" +
      "<div class='d-flex align-items-end'>" +
      "<div class='message-box-end bg-primary text-white'><p class='no-margin'><span class='user-message-span' style='font-size: 125%;'>" +
      userMessage +
      '</span></p></div></div></div>',
  );

  //make this message from the user a static mq field
  let lastMessageParent = $('#calculatorDialog .user-message').last();
  MQ.StaticMath(lastMessageParent.find('.user-message-span')[0]);
  lastMessageParent
    .find('.user-message-span .mq-root-block')
    .addClass('d-flex flex-wrap');

  let problemID = $('#unique-problem-id').html();
  if (!problemID) {
    SaveNewProblem().then(function () {
      GetResponse(userMessage);
    });
  } else {
    GetResponse(userMessage);
  }
}

function GetResponse(userMessageLatex) {}

function SetCalculatorHeight() {
  let newHeight = $('#algebra').height() - 38;
  $('#calculatorDialog').css('height', newHeight + 'px');
  let simplebarWrapper = $('#calculatorDialog .simplebar-content-wrapper');
  simplebarWrapper.animate(
    { scrollTop: simplebarWrapper.prop('scrollHeight') },
    'slow',
  );
}
