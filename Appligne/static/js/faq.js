function activateFaqToggle() {
    $('.faq-question').off('click').on('click', function () {
        var answer = $(this).next('.faq-answer');
        var icon = $(this).find('.toggle-icon');

        $('.faq-answer').not(answer).slideUp();
        $('.toggle-icon').not(icon).text('➕');

        answer.slideToggle(200, function () {
            icon.text($(this).is(':visible') ? '➖' : '➕');
        });
    });
}

function fetchFAQs(page = 1) {
    const role = $('#role').val();
    const keyword = $('#keyword').val();

    $('#loader').show();
    $('#faq-container').css('opacity', '0.3');

    $.ajax({
        url: window.location.pathname,
        type: 'GET',
        data: {
            role: role,
            keyword: keyword,
            page: page
        },
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        success: function (data) {
            $('#faq-container').html(data.html);
            $('#faq-pagination').html(data.pagination);
            activateFaqToggle();
            activatePaginationLinks(); // Important !
        },
        error: function () {
            alert("Erreur lors du chargement des FAQ.");
        },
        complete: function () {
            $('#loader').hide();
            $('#faq-container').css('opacity', '1');
        }
    });
}

function activatePaginationLinks() {
    $('.page-ajax').off('click').on('click', function (e) {
        e.preventDefault();
        const url = new URL(this.href, window.location.origin);
        const page = url.searchParams.get('page');
        fetchFAQs(page);
    });
}

$(document).ready(function () {
    activateFaqToggle();
    activatePaginationLinks();

    $('#role, #keyword').on('change keyup', function () {
        fetchFAQs();
    });

    $('#role-filter-form').on('submit', function (e) {
        e.preventDefault();
        fetchFAQs();
    });
});
