function InitializeCalculator() {
  $('.response .d-flex.align-items-end.d-none').each(function () {
    $(this).removeClass('d-none');
    $(this).find('p.message-load-animation').addClass('d-none');
    $(this).find('p.content.d-none').removeClass('d-none');
    $(this).parent().find('.fs-xs.text-muted.d-none').removeClass('d-none');
  });

  $('.latex-message-span').each(function () {
    MQ.MathField($(this)[0]);
  });

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
        if (
          calculatorField.latex().length &&
          calculatorField.latex().length < 250
        ) {
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
      "<div class='message-box-end bg-primary text-white'><p class='no-margin'><span class='latex-message-span' style='font-size: 125%;'>" +
      userMessage +
      '</span></p></div></div></div>',
  );

  //make this message from the user a static mq field
  let lastMessageParent = $('#calculatorDialog .user-message').last();
  MQ.StaticMath(lastMessageParent.find('.latex-message-span')[0]);

  //lastMessageParent.find('.latex-message-span .mq-root-block').addClass('d-flex flex-wrap');

  let problemID = $('#unique-problem-id').html();
  if (!problemID) {
    SaveNewProblem().then(function () {
      GetResponse(userMessage, 'SubmitUserMessage');
    });
  } else {
    GetResponse(userMessage, 'SubmitUserMessage');
  }
}

function GetResponse(userMessageLatex, callerFunctionName) {
  let timeBetweenMessages = 4500;
  let responseParameters =
    'sandbox=Algebra&problem_id=' + $('#unique-problem-id').html();
  responseParameters += '&message=' + encodeURIComponent(userMessageLatex);
  responseParameters += '&caller=' + encodeURIComponent(callerFunctionName);

  $('#calculatorDialog .simplebar-content').append(
    "<div class='mb-3 w-75 response'></div>",
  );
  $('#calculatorDialog .response')
    .last()
    .load('/calculator/get-response/?' + responseParameters, function () {
      let lastResponseParent = $('#calculatorDialog .response').last();
      let lastResponses = lastResponseParent.find('.d-flex.align-items-end');

      // For each message in the response to the last user message (it might be split up into more than 1)
      // show the message load animation and do not display the message
      lastResponses.first().removeClass('d-none');
      lastResponseParent
        .find('.fs-xs.text-muted')
        .first()
        .removeClass('d-none');
      //Now, since each response message for the last user message is hidden, this will make the messages appear
      //and make the loading animation disappear every 1.2 seconds
      let responseIndex = 0;
      let appearInterval = setInterval(function () {
        //code that makes responses appear
        lastResponses
          .eq(responseIndex)
          .find('p.no-margin')
          .each(function () {
            if ($(this).hasClass('message-load-animation')) {
              $(this).addClass('d-none');
            } else {
              $(this).removeClass('d-none');
            }
          });
        responseIndex++;
        if (responseIndex < lastResponses.length) {
          lastResponses.eq(responseIndex).removeClass('d-none');
          lastResponseParent
            .find('.fs-xs.text-muted')
            .eq(responseIndex)
            .removeClass('d-none');
        }

        lastResponseParent.find('.latex-message-span').each(function () {
          MQ.StaticMath($(this)[0]);
        });

        //lastResponseParent.find('.latex-message-span .mq-root-block').addClass('d-flex flex-wrap');

        let simplebarWrapper = $(
          '#calculatorDialog .simplebar-content-wrapper',
        );
        simplebarWrapper.animate(
          { scrollTop: simplebarWrapper.prop('scrollHeight') },
          'slow',
        );
      }, timeBetweenMessages);

      //Once the last response is shown...
      let calcInputField = MQ.MathField($('#calculatorInput')[0]);
      setTimeout(
        function () {
          let stepID = lastResponseParent.find('.badge-step-id').html();
          let side = 'right';
          let badgeObj = $(
            '#step' + stepID + ' button.check-rewrite-right .badge',
          );
          if (lastResponseParent.find('.new-badge-count-left').length) {
            badgeObj = $(
              '#step' + stepID + ' button.check-rewrite-left .badge',
            );
            side = 'left';
          }
          badgeObj.html(
            $(lastResponseParent)
              .find('.new-badge-count-' + side)
              .html(),
          );
          if (lastResponseParent.find('.danger').length) {
            badgeObj.removeClass('bg-faded-info text-info');
            badgeObj.addClass('bg-faded-danger text-danger');
          }

          if (lastResponseParent.find('.finished').length) {
            LockEverything();
            stopConfetti = false;
            poof();
          }

          $('#calculatorSubmit').prop('disabled', false);
          if (calcInputField) {
            calcInputField.config({
              handlers: {
                enter: function () {
                  if (
                    calcInputField.latex().length &&
                    calcInputField.latex().length < 250
                  ) {
                    SubmitUserMessage();
                    calcInputField.latex('');
                  }
                },
              },
            });
          }

          clearInterval(appearInterval);
        },
        lastResponses.length * timeBetweenMessages + 100,
      );

      let simplebarWrapper = $('#calculatorDialog .simplebar-content-wrapper');
      simplebarWrapper.animate(
        { scrollTop: simplebarWrapper.prop('scrollHeight') },
        'slow',
      );
    });
}

function SetCalculatorHeight() {
  let newHeight = $('#algebra').height() - 38;
  $('#calculatorDialog').css('height', newHeight + 'px');
  let simplebarWrapper = $('#calculatorDialog .simplebar-content-wrapper');
  simplebarWrapper.animate(
    { scrollTop: simplebarWrapper.prop('scrollHeight') },
    'slow',
  );
}
