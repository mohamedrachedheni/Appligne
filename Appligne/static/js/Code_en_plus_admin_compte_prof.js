document.addEventListener('DOMContentLoaded', () => {
    // Références des éléments
    const inputField = document.querySelector('#professeurs'); // Champ d'entrée principal
    const dropdownMenu = document.querySelector('.dropdown-menu'); // Menu déroulant

    if (inputField && dropdownMenu) {
        // Désactiver l'autocomplétion du navigateur pour éviter le menu natif
        inputField.setAttribute('autocomplete', 'off');

        // Écouter les événements de saisie pour filtrer le menu
        inputField.addEventListener('input', () => {
            const searchText = inputField.value.toLowerCase().trim(); // Texte saisi en minuscules et sans espaces
            let hasVisibleItems = false; // Flag pour vérifier si des items correspondent

            // Filtrer les items en fonction du texte saisi
            const dropdownItems = dropdownMenu.querySelectorAll('.dropdown-prof');
            dropdownItems.forEach(item => {
                const itemText = item.getAttribute('data-value').toLowerCase();

                if (itemText.startsWith(searchText)) {
                    item.style.display = ''; // Afficher l'item
                    hasVisibleItems = true;
                } else {
                    item.style.display = 'none'; // Cacher l'item
                }
            });

            // Afficher ou masquer le menu déroulant selon les résultats
            if (searchText !== '' && hasVisibleItems) {
                dropdownMenu.classList.add('show');
            } else {
                dropdownMenu.classList.remove('show');
            }
        });

        // Gérer la sélection d'un professeur
        dropdownMenu.addEventListener('click', event => {
            const item = event.target.closest('.dropdown-prof');
            if (item) {
                event.preventDefault(); // Empêcher le comportement par défaut

                // Récupérer les informations du professeur sélectionné
                const selectedId = item.getAttribute('data-id');
                const selectedValue = item.getAttribute('data-value');

                // Mettre à jour les champs du formulaire
                inputField.value = selectedValue;
                document.querySelector('#selected_professeur').value = selectedId;

                // Masquer le menu déroulant
                dropdownMenu.classList.remove('show');

                // Soumettre le formulaire
                const form = document.querySelector('#professeurForm');
                if (form) form.submit();
            }
        });

        // Gérer le focus sur le champ pour afficher le menu
        inputField.addEventListener('focus', () => {
            const dropdownItems = dropdownMenu.querySelectorAll('.dropdown-prof');
            let hasVisibleItems = Array.from(dropdownItems).some(item => item.style.display !== 'none');

            if (hasVisibleItems) {
                dropdownMenu.classList.add('show');
            }
        });

        // Fermer le menu déroulant lorsqu'on clique en dehors
        document.addEventListener('click', event => {
            if (!inputField.contains(event.target) && !dropdownMenu.contains(event.target)) {
                dropdownMenu.classList.remove('show');
            }
        });

        // Empêcher l'affichage en double lors des interactions
        dropdownMenu.addEventListener('show.bs.dropdown', () => {
            dropdownMenu.classList.remove('show');
        });
    }
});

//***********************************  liée à tous les pages contenant un champ input téléphone début   *********************** */
// Lien vers Font Awesome
document.write('<script src="https://kit.fontawesome.com/1d95b4176e.js" crossorigin="anonymous"></script>');

//<!-- Appliquer le masque de saisie -->
document.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"'
    + 'integrity="sha384-C6RzsynM9kWDrMNeT87bh95OGNyZPhcTNXj1NW7RuBCsyN/o0jlpcV8Qyq46cDfL"' +
    'crossorigin="anonymous" ></script>');

$(document).ready(function () {
    $('#numero_telephone_id').inputmask('99 99 99 99 99');
});
//***********************************  liée à tous les pages contenant un champ input téléphone fin   *********************** */

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

    // ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome
    function supprimerDiv(divId) {
        var div = document.getElementById(divId);
        if (div) {
            div.parentNode.removeChild(div);
    }}
// ****************************  pour plusieur pages   fin  ***********************

//gérer le champ prix-heure pour afficher des nombres décimaux
$(document).ready(function(){
    $('.prix-heure').inputmask({
        alias: 'numeric',
        groupSeparator: '',
        digits: 2,
        digitsOptional: false,
        placeholder: '0',
        rightAlign: false,
        autoUnmask: true,
        integerDigits: 3, // Allow up to 3 digits before the decimal point
        max: 999.99,
        allowMinus: false,
        suffix: ' €/h' // Add the euro per hour unit
    });
});


