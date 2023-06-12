let currentPaginateBy = 10;
let currentPageNum = 1;
let equationSearch = null;

function InitializeTable() {
  $('#unsolvedCheck, #solvedCheck').change(function () {
    if (
      !$('#unsolvedCheck').prop('checked') &&
      !$('#solvedCheck').prop('checked')
    ) {
      $(this).prop('checked', 'checked');
    } else {
      ChangePaginateBy();
    }
  });

  $(
    '#step-count-up, #step-count-down, #last-viewed-up, #last-viewed-down, #start-date-up, #start-date-down',
  ).click(function () {
    if ($(this).hasClass('active')) {
    } else {
      $(
        '#step-count-up, #step-count-down, #last-viewed-up, #last-viewed-down, #start-date-up, #start-date-down',
      ).each(function () {
        $(this).removeClass('active');
      });
      $(this).addClass('active');

      GoToPage();
    }
  });

  let equationField = MQ.MathField($('#equation-filter-input')[0]);

  let timeout = null;
  equationField.config({
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
            equationField
              .latex()
              .includes('randomstringnoonewillevertypeinhopefully')
          ) {
          } else {
            equationSearch = equationField.latex();
            ChangePaginateBy();
          }
        }, 500);
      },
    },
  });

  let equationFilterTextArea = $('#equation-filter-input textarea');
  equationFilterTextArea.focus(function () {
    $('.filter-input-border').css({
      'border-color': 'var(--ar-gray-700)',
      outline: '0',
      'box-shadow': 'unset',
    });
  });
  equationFilterTextArea.blur(function () {
    $('.filter-input-border').css({
      'border-color': '',
      outline: '',
      'box-shadow': '',
    });
  });

  ChangePaginateBy();
}

function GetRecentTableFilter() {
  let filterParams;

  if ($('#unsolvedCheck').prop('checked')) {
    filterParams = 'status=unsolved';
  }
  if ($('#solvedCheck').prop('checked')) {
    if (filterParams === 'status=unsolved') {
      filterParams = 'status=all';
    } else {
      filterParams = 'status=solved';
    }
  }

  $(
    '#step-count-up, #step-count-down, #last-viewed-up, #last-viewed-down, #start-date-up, #start-date-down',
  ).each(function () {
    if ($(this).hasClass('active')) {
      let order_by_id = $(this).prop('id');
      if (filterParams.length) {
        filterParams += '&order_by=' + order_by_id;
      } else {
        filterParams = 'order_by=' + order_by_id;
      }
    }
  });

  if (equationSearch) {
    filterParams += '&equation=' + equationSearch;
  }

  return filterParams;
}

function GoToPage() {
  let filter = GetRecentTableFilter();
  $('.tab-pane#recent tbody').load(
    '/algebra/recent-table/?update_body=true&paginate_by=' +
      currentPaginateBy +
      '&page=' +
      currentPageNum +
      '&' +
      filter,
    function () {
      //initialize static equations
      $('.recentEquation').each(function () {
        MQ.StaticMath($(this)[0]);
      });

      //update pagination
      $('.page-item button').each(function () {
        $(this).parent().removeClass('active');
        $(this).prop('disabled', false);
        if (parseInt($(this).html()) === currentPageNum) {
          $(this).parent().addClass('active');
          $(this).prop('disabled', true);
        }
      });
    },
  );
}

function ChangePaginateBy() {
  let filter = GetRecentTableFilter();
  $('#pagination').load(
    '/algebra/recent-table/?update_pagination=true&paginate_by=' +
      currentPaginateBy +
      '&' +
      filter,
    function () {
      currentPageNum = 1;

      GoToPage();

      $('.page-item button').click(function () {
        currentPageNum = parseInt($(this).html());
        GoToPage();
      });

      $('#paginateBySelect').on('change', function () {
        currentPaginateBy = parseInt($(this).val());
        ChangePaginateBy();
      });

      if (currentPaginateBy % 10 !== 0) {
        currentPaginateBy = parseInt(
          $('#paginateBySelect option:last-child').val(),
        );
      }

      $('#paginateBySelect option[value=' + currentPaginateBy + ']').attr(
        'selected',
        'selected',
      );
    },
  );
}
