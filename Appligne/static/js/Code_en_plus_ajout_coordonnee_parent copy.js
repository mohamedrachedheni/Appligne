//*******************************  ClassName("form-control form-control-date") debut  *********************************** */
// Lien vers Pikaday
document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/pikaday/1.8.0/pikaday.min.js"></script>');

// Fonction pour configurer Pikaday pour un élément spécifique selon son ID
function configurerPikaday(indice) {
    // Date par défaut
    var defaultDate = new Date();

    // Utilisation de la bibliothèque Pikaday pour faciliter la sélection de la date
    var picker = new Pikaday({
        field: document.getElementById('date_id_' + indice),
        format: 'DD/MM/YYYY', // Format de la date en français
        i18n: {
            previousMonth: 'Mois précédent',
            nextMonth: 'Mois suivant',
            months: [
                'Janvier',
                'Février',
                'Mars',
                'Avril',
                'Mai',
                'Juin',
                'Juillet',
                'Août',
                'Septembre',
                'Octobre',
                'Novembre',
                'Décembre'
            ],
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            weekdaysShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
        },
        defaultDate: defaultDate, // Définir la date par défaut
        onSelect: function (date) {
            var formattedDate = ("0" + date.getDate()).slice(-2) + "/" + ("0" + (date.getMonth() + 1)).slice(-2) + "/" + date.getFullYear();
            document.getElementById('date_id_' + indice).value = formattedDate;
        }
    });
};

    // relative à tous les pages contenants ClassName("form-control form-control-date")
    // Appeler Pikaday au chargement de toute page contenant la class = "form-control form-control-date"
    // relatif aux Input des date dont ID = "date_id_(i + 1)"
    document.addEventListener('DOMContentLoaded', function () {
        var listDiv = document.getElementsByClassName("form-control form-control-date");
        for (var i = 0; i < listDiv.length; i++) {
            configurerPikaday(i+1)
            
        }   
    });
    //*******************************  ClassName("form-control form-control-date") fin *********************************** */


//***********************************  liée à tous les pages contenant un champ input téléphone début   *********************** */
// Lien vers Font Awesome
document.write('<script src="https://kit.fontawesome.com/1d95b4176e.js" crossorigin="anonymous"></script>');

//<!-- Appliquer le masque de saisie -->
document.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"'
    + 'integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL"' +
    'crossorigin="anonymous" ></script>');

$(document).ready(function () {
    $('#phone_id').inputmask('99 99 99 99 99');
});
//***********************************  liée à tous les pages contenant un champ input téléphone fin   *********************** */
