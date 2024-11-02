

// document.addEventListener("DOMContentLoaded", function() {
//     // Gestion des liens de pagination avec localStorage
//     var savedPage = localStorage.getItem('currentPage');
//     if (savedPage) {
//         var pageLink = document.querySelector('.pagination a.page-link[href="?page=' + savedPage + '"]');
//         if (pageLink) {
//             pageLink.focus();
//         }
//     }

//     var pageLinks = document.querySelectorAll('.pagination a.page-link');
//     pageLinks.forEach(function(link) {
//         link.addEventListener('click', function() {
//             var pageNumber = this.getAttribute('href').split('page=')[1];
//             localStorage.setItem('currentPage', pageNumber);
//         });
//     });

// });
