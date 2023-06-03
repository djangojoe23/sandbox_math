let MQ = null;
let studentID = null;

function waitForElement(elementPath, callBack) {
  window.setTimeout(function () {
    if ($(elementPath).length) {
      callBack(elementPath, $(elementPath));
    } else {
      console.log('waiting...');
      waitForElement(elementPath, callBack);
    }
  }, 500);
}

$(document).ready(function () {
  MQ = MathQuill.getInterface(2);
  studentID = $('#userID').html();

  $('#offcanvasMenu a').click(function () {
    if ($(this).html() !== 'New Blank') {
      $('.navbar div.h6').html($(this).html());
    }
  });

  // This allows the algebra offcanvas menu to close when you click off it (not just with the close button)
  document.body.addEventListener('click', function (e) {
    if ($('.offcanvas.show').length > 0) {
      let myOffcanvas = window.bootstrap.Offcanvas.getInstance(
        $('#offcanvasMenu')[0],
      );
      myOffcanvas.hide();
    }
  });

  if ($('.algebra-step').length) {
    //LoadSavedProblem()
  } else {
    $('#algebra').prepend(
      $('<div id="step0" class="step algebra-step pb-1 pt-0" style=""></div>'),
    );
    $('#expressionHelp').append($('<div id="step0Help"></div>'));
    $('#step0Help').append(
      $(
        '<div class="left-help-button-title"></div><div class="left-help-button-content"></div>',
      ),
      $(
        '<div class="right-help-button-title"></div><div class="right-help-button-content"></div>',
      ),
    );
    $(
      '#step0Help .left-help-button-title, #step0Help .right-help-button-title',
    ).html('Define the Equation');
    $(
      '#step0Help .left-help-button-content, #step0Help .right-help-button-content',
    ).html('Use the dropdown in the first step to define an equation.');
    waitForElement('#step0', function () {
      $('#step0').load('/algebra/start-new/', function () {
        InitializeNewStep('step0');
      });
    });
  }
});

function InitializeNewStep(stepID) {
  MQ.StaticMath($('#' + stepID + ' .mq-equal-sign')[0]);
  $('#' + stepID + ' .left-mq-input, #' + stepID + ' .right-mq-input').each(
    function () {
      InitializeMathQuillInput($(this));
    },
  );

  $('#' + stepID + ' .step-type-dropdown > div.dropdown-menu button').click(
    function () {
      void StepTypeChanged($(this));
    },
  );

  $('#' + stepID + ' .delete-step button').click(function () {
    //void DeleteStep(stepID)
  });

  $(
    '#' + stepID + ' .left-help-button, #' + stepID + ' .right-help-button',
  ).click(function () {
    // let thisButton = $(this)
    // $(this).css('pointer-events', 'none')
    // ToggleExpressionHelp(stepID, $(this).prop("class")).then(r => {
    //     setTimeout(function(){
    //         thisButton.css('pointer-events', '')
    //     }, 1000)
    // })
  });
}

function InitializeMathQuillInput(mqInputObject) {
  let mathField = MQ.MathField(mqInputObject[0]);

  let timeout = null;
  mathField.config({
    supSubsRequireOperand: true,
    restrictMismatchedBrackets: true,
    autoOperatorNames: 'randomstringnoonewillevertypeinhopefully',
    autoCommands: 'randomstringnoonewillevertypeinhopefully',
    maxDepth: 1,
    handlers: {
      edit: function () {
        $('#newStepButton').prop('disabled', true);
        $('#checkSolutionButton').prop('disabled', true);
        if (timeout != null) {
          clearTimeout(timeout);
        }
        timeout = setTimeout(function () {
          if (
            mathField
              .latex()
              .includes('randomstringnoonewillevertypeinhopefully')
          ) {
            // Do nothing
          } else {
            //ExpressionChanged(inputObject)
          }
        }, 500);
      },
    },
  });

  let stepID = mqInputObject.parents('.step').attr('id');
  let textAreas = $(
    '#' +
      stepID +
      ' .left-mq-input textarea, #' +
      stepID +
      ' .right-mq-input textarea',
  );
  let dropdownButton = $('#' + stepID + ' .step-type-dropdown button');
  textAreas.focus(function () {
    $('#' + stepID).addClass('active');
    dropdownButton.removeClass('btn-secondary');
    dropdownButton.addClass('btn-primary');
    if ($(this).parent().parent().hasClass('left-mq-input')) {
      $('#' + stepID + ' .left-expr-border').css({
        'border-color': 'var(--ar-gray-700)',
        outline: '0',
        'box-shadow': 'unset',
      });
      $('#' + stepID + ' .left-help-button i').css({
        color: 'var(--ar-gray-700)',
      });
    } else {
      $('#' + stepID + ' .right-expr-border').css({
        'border-color': 'var(--ar-gray-700)',
        outline: '0',
        'box-shadow': 'unset',
      });
      $('#' + stepID + ' .right-help-button i').css({
        color: 'var(--ar-gray-700)',
      });
    }
  });
  textAreas.blur(function () {
    $('#' + stepID).removeClass('active');
    dropdownButton.removeClass('btn-primary');
    dropdownButton.addClass('btn-secondary');
    if ($(this).parent().parent().hasClass('left-mq-input')) {
      $('#' + stepID + ' .left-expr-border').css({
        'border-color': '',
        outline: '',
        'box-shadow': '',
      });
      $('#' + stepID + ' .left-help-button i').css({ color: '' });
    } else {
      $('#' + stepID + ' .right-expr-border').css({
        'border-color': '',
        outline: '',
        'box-shadow': '',
      });
      $('#' + stepID + ' .right-help-button i').css({ color: '' });
    }
  });
}

function SaveNewProblem() {
  return new Promise((resolve) => {
    let uniqueProblemID = $('#unique-problem-id').html();
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    if (!uniqueProblemID.length) {
      $('#addStepButton').prop('disabled', true);
      $('#checkSolutionButton').prop('disabled', true);
      $.ajax({
        url: '/algebra/save-new/',
        type: 'GET',
        headers: { 'X-CSRFToken': csrfToken },
        data: {},
      })
        .done(function (response) {
          $('#unique-problem-id').html(response['unique-problem-id']);
          window.history.replaceState(
            'Problem ' + response['unique-problem-id'],
            'Title of this problem!',
            '/algebra/' + response['unique-problem-id'],
          );
          let newStepID = 'step' + response['unique-step-id'];
          $('#step0').attr('id', newStepID);
          $('#step0Help').attr('id', newStepID + 'Help');
          InitializeNewStep(newStepID);
          $('#addStepButton').prop('disabled', false);
          $('#checkSolutionButton').prop('disabled', false);
          resolve(newStepID);
        })
        .fail(function (error) {
          console.log(error);
          $('#addStepButton').prop('disabled', false);
          $('#checkSolutionButton').prop('disabled', false);
          resolve(error);
        });
    } else {
      resolve(-1);
    }
  });
}

async function StepTypeChanged(menuButtonObject) {
  let stepID = menuButtonObject.parents('.step').attr('id');
  if (stepID === 'step0') {
    stepID = await SaveNewProblem();
  }

  let selectedHTML = menuButtonObject.html();

  let deleteStepButton = $('#' + stepID + ' .delete-step');
  //let rewriteButtons = $("#" + stepID + " .check-rewrite-buttons")
  if (selectedHTML.includes('Delete')) {
    deleteStepButton.css('visibility', '');
    //rewriteButtons.addClass("d-none")
  } else if (selectedHTML.includes('Rewrite')) {
    //rewriteButtons.removeClass("d-none")
    deleteStepButton.css('visibility', 'hidden');
  } else {
    deleteStepButton.css('visibility', 'hidden');
    //rewriteButtons.addClass("d-none")
  }

  let toggleButton = $(
    '#' + stepID + ' .step-type-dropdown > button.dropdown-toggle',
  );

  if (toggleButton.html() === selectedHTML) {
    //do nothing
  } else {
    toggleButton.html(selectedHTML);
  }
}
