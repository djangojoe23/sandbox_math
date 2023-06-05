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

  if ($('#unique-problem-id').html().length) {
    //Load Existing Problem
    $('.algebra-step').each(function () {
      InitializeNewStep($(this).attr('id'));
      //This will populate the variable options menu
      void ExpressionChanged($('.algebra-step:first-child .left-mq-input'));
    });
  } else {
    //Start New Problem
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

  $('#newStepButton').click(function () {
    AttemptNewStep();
  });
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
    void DeleteStep(stepID);
  });

  let helpButtons = $(
    '#' + stepID + ' .left-help-button, #' + stepID + ' .right-help-button',
  );
  helpButtons.off('click');
  helpButtons.click(function () {
    let thisButton = $(this);
    $(this).css('pointer-events', 'none');
    ToggleExpressionHelp(stepID, $(this)).then(function () {
      // this code runs 2 seconds after the help button is displayed
      // this is to avoid rapid repetitive help clicks
      setTimeout(function () {
        thisButton.css('pointer-events', '');
      }, 2000);
    });
  });

  const popoverTriggerList = document.querySelectorAll(
    '[data-bs-toggle="popover"]',
  );
  const popoverList = [...popoverTriggerList].map(
    (popoverTriggerEl) => new bootstrap.Popover(popoverTriggerEl),
  );
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
            void ExpressionChanged(mqInputObject);
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
      ToggleNewAndCheckButtons(true);
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
            '',
            '/algebra/' + response['unique-problem-id'],
          );
          let newStepID = 'step' + response['unique-step-id'];
          $('#step0').attr('id', newStepID);
          $('#step0Help').attr('id', newStepID + 'Help');
          InitializeNewStep(newStepID);
          ToggleNewAndCheckButtons(false);
          resolve(newStepID);
        })
        .fail(function (error) {
          console.log(error);
          ToggleNewAndCheckButtons(false);
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

    ToggleNewAndCheckButtons(true);
    let uniqueStepID = parseInt(stepID.substring('step'.length, stepID.length));
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    $.ajax({
      url: '/algebra/update-step-type/',
      type: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      data: { 'step-id': uniqueStepID, 'step-type': selectedHTML },
    })
      .done(function (response) {
        UpdateAllExpressionHelp(response['mistakes']);
        let stepNumber = parseInt(
          $('#' + stepID + ' .step-number-inner').html(),
        );
        if (stepNumber === 1) {
          //TODO tell the server to forget the variable selected if it isn't present in the equation
          let varToggle = $('#variableDropdown .dropdown-toggle');
          if (selectedHTML.includes('Define')) {
            if ($('#variableDropdown > div.dropdown-menu button').length > 0) {
              // varToggle.prop("disabled", false)
              varToggle.html(response['selected_variable']);
            }
          } else {
            // varToggle.prop("disabled", true)
            varToggle.html('');
            // i don't tell the server to forget the variable they had selected here
          }
        }
        ToggleNewAndCheckButtons(false);
      })
      .fail(function () {
        ToggleNewAndCheckButtons(false);
      });
  }
}

async function ExpressionChanged(expressionObject) {
  let newExpression = MQ(expressionObject[0]).latex();

  let stepID = expressionObject.parents('.step').attr('id');
  if (stepID === 'step0') {
    stepID = await SaveNewProblem();
  }
  let uniqueStepID = parseInt(stepID.substring('step'.length, stepID.length));

  let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  $.ajax({
    url: '/algebra/update-expression/',
    type: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    data: {
      'step-id': uniqueStepID,
      expression: newExpression,
      side: expressionObject.attr('class'),
    },
  })
    .done(function (response) {
      UpdateAllExpressionHelp(response['mistakes']);
      let stepNumber = parseInt($('#' + stepID + ' .step-number-inner').html());
      if (stepNumber === 1) {
        let varToggle = $('#variableDropdown .dropdown-toggle');
        let varMenu = $('#variableDropdown .dropdown-menu');

        varToggle.html(response['selected_variable']);
        varMenu.html('');
        if (response['variable_options'].length > 0) {
          // varToggle.prop("disabled", false)
          for (let i = 0; i < response['variable_options'].length; i++) {
            varMenu.append(
              '<button class ="dropdown-item">' +
                response['variable_options'][i] +
                '</button>',
            );
          }
        } else if (varToggle.html().length === 0) {
          // varToggle.prop("disabled", true)
        }

        $('#variableDropdown > div.dropdown-menu button').click(function () {
          VariableChanged($(this).html());
        });
      }

      ToggleNewAndCheckButtons(false);

      SetCalculatorHeight();
    })
    .fail(function () {
      ToggleNewAndCheckButtons(false);
    });
}

function VariableChanged(varSelected) {
  $('#variableDropdown .dropdown-toggle').html(varSelected);
  ToggleNewAndCheckButtons(true);

  let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  $.ajax({
    url: '/algebra/update-variable/',
    type: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    data: {
      'problem-id': parseInt($('#unique-problem-id').html()),
      variable: varSelected,
    },
  })
    .done(function (response) {
      UpdateAllExpressionHelp(response['mistakes']);

      ToggleNewAndCheckButtons(false);
    })
    .fail(function () {
      ToggleNewAndCheckButtons(false);
    });
}

function AttemptNewStep() {
  let problemID = $('#unique-problem-id').html();
  if (problemID.length === 0) {
    console.log('alert!');
  } else {
    ToggleNewAndCheckButtons(true);
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    $.ajax({
      url: '/algebra/attempt-new-step/',
      type: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      data: { 'problem-id': problemID },
    })
      .done(function (response) {
        if (response['next_action'] === 'append') {
          NewStep(response['new_step_id']);
        } else if (response['next_action'] === 'alert') {
          console.log('alert!');
        }
        ToggleNewAndCheckButtons(false);
      })
      .fail(function () {
        ToggleNewAndCheckButtons(false);
      });
  }
}

function NewStep(uniqueStepID) {
  let stepID = 'step' + uniqueStepID;

  $(
    '<div id="' + stepID + '" class="step algebra-step pb-1" style=""></div>',
  ).insertBefore('#newStepButtonStep');

  $('#expressionHelp').append($('<div id="' + stepID + 'Help"></div>'));
  $('#' + stepID + 'Help').append(
    $(
      '<div class="left-help-button-title"></div><div class="left-help-button-content"></div>',
    ),
    $(
      '<div class="right-help-button-title"></div><div class="right-help-button-content"></div>',
    ),
  );
  $(
    '#' +
      stepID +
      'Help .left-help-button-title, #' +
      stepID +
      'Help .right-help-button-title',
  ).html('Define the Expression');
  $(
    '#' +
      stepID +
      'Help .left-help-button-content, #' +
      stepID +
      'Help .right-help-button-content',
  ).html('This is blank. Type in math expressions to define an equation!');

  $('#' + stepID).load(
    '/algebra/new-step/?problem-id=' + $('#unique-problem-id').html(),
    function () {
      InitializeNewStep(stepID);

      $('#checkSolutionButton').addClass('d-none');
    },
  );
}

async function DeleteStep(stepID) {
  ToggleNewAndCheckButtons(true);
  let uniqueStepID = parseInt(stepID.substring('step'.length, stepID.length));
  let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
  $.ajax({
    url: '/algebra/delete-step/',
    type: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    data: { 'step-id': uniqueStepID },
  })
    .done(function (response) {
      $('#' + stepID).remove();
      let stepCount = 1;
      $('.step-number-inner').each(function () {
        $(this).html(stepCount);
        stepCount++;
      });

      UpdateAllExpressionHelp(response['mistakes']);

      ToggleNewAndCheckButtons(false);

      SetCalculatorHeight();
    })
    .fail(function () {
      ToggleNewAndCheckButtons(false);
    });
}

function UpdateAllExpressionHelp(updatedHelpDict) {
  for (const [stepID, helpDict] of Object.entries(updatedHelpDict)) {
    $('#step' + stepID + 'Help .left-help-button-title').html(
      helpDict[0]['title'],
    );
    $('#step' + stepID + 'Help .left-help-button-content').html(
      helpDict[0]['content'],
    );

    $('#step' + stepID + 'Help .right-help-button-title').html(
      helpDict[1]['title'],
    );
    $('#step' + stepID + 'Help .right-help-button-content').html(
      helpDict[1]['content'],
    );
  }
}

async function ToggleExpressionHelp(stepID, exprObject) {
  let exprClass = '';
  if (exprObject.hasClass('left-help-button')) {
    exprClass = 'left-help-button';
  } else if (exprObject.hasClass('right-help-button')) {
    exprClass = 'right-help-button';
  } else {
    console.log('toggle expression help error!');
  }
  let helpTitle = $('#' + stepID + 'Help .' + exprClass + '-title').html();
  let helpContent = $('#' + stepID + 'Help .' + exprClass + '-content').html();

  const popover = bootstrap.Popover.getOrCreateInstance(
    $('#' + stepID + ' .' + exprClass)[0],
  );
  popover.setContent({
    '.popover-header': helpTitle,
    '.popover-body': helpContent,
  });

  let uniqueStepID = parseInt(stepID.substring('step'.length, stepID.length));
  if (uniqueStepID !== 0) {
    ToggleNewAndCheckButtons(true);
    let csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    $.ajax({
      url: '/algebra/update-help-click/',
      type: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      data: { 'step-id': uniqueStepID, side: exprClass },
    })
      .done(function () {
        ToggleNewAndCheckButtons(false);
      })
      .fail(function () {
        ToggleNewAndCheckButtons(false);
      });
  }
}

function ToggleNewAndCheckButtons(isDisabled) {
  $('#newStepButton').prop('disabled', isDisabled);
  $('#checkSolutionButton').prop('disabled', isDisabled);
}
