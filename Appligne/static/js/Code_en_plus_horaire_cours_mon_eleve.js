//*******************************  ClassName("form-control form-control-date") debut  *********************************** */
// Lien vers Pikaday
document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/pikaday/1.8.0/pikaday.min.js"></script>');


function configurerPikaday(indice) {
    var defaultDate = new Date();

    var field = document.getElementById('date_id_' + indice);

    var picker = new Pikaday({
        field: field,
        format: 'DD/MM/YYYY',
        i18n: {
            previousMonth: 'Mois précédent',
            nextMonth: 'Mois suivant',
            months: [
                'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
            ],
            weekdays: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
            weekdaysShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam']
        },
        defaultDate: defaultDate,
        onSelect: function (date) {
            var formattedDate =
                ("0" + date.getDate()).slice(-2) + "/" +
                ("0" + (date.getMonth() + 1)).slice(-2) + "/" +
                date.getFullYear();

            field.value = formattedDate;

            // Redonner le focus après la fermeture du calendrier
            requestAnimationFrame(function () {
                field.focus();
            });
        }
    });

    // Éviter que Pikaday perde le focus après clic
    field.addEventListener('blur', function (e) {
        if (picker.isVisible()) {
            e.preventDefault();
            requestAnimationFrame(function () {
                field.focus();
            });
        }
    });
}

// Appeler Pikaday au chargement de toute page contenant la class = "form-control form-control-date"
// relatif aux Input des date dont ID = "date_id_(i + 1)"
document.addEventListener('DOMContentLoaded', function () {
    var listDiv = document.getElementsByClassName("form-control form-control-date");
    for (var i = 0; i < listDiv.length; i++) {
        configurerPikaday(i + 1);
    }
});



// relative à tous les pages contenants ClassName("form-control form-control-date")
// Appeler Pikaday au chargement de toute page contenant la class = "form-control form-control-date"
// relatif aux Input des date dont ID = "date_id_(i + 1)"
document.addEventListener('DOMContentLoaded', function () {
    var listDiv = document.getElementsByClassName("form-control form-control-date");
    for (var i = 0; i < listDiv.length; i++) {
        configurerPikaday(i + 1)

    }
});
//*******************************  ClassName("form-control form-control-date") fin *********************************** */

document.addEventListener("DOMContentLoaded", function () {
    var timeInputs = document.querySelectorAll('.form-control-heure');

    function validateTimeInput(input) {
        var timeValue = input.value;
        var [hours, minutes] = timeValue.split(':').map(Number);
        var errorElement = input.nextElementSibling;

        // Si l'élément suivant n'existe pas ou n'a pas la classe 'error-message', on le crée
        if (!errorElement || !errorElement.classList.contains('error-message')) {
            errorElement = document.createElement('div');
            errorElement.classList.add('error-message');
            errorElement.style.color = 'red';
            input.parentNode.insertBefore(errorElement, input.nextSibling);
        }

        if (isNaN(hours) || isNaN(minutes) || hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
            input.classList.add('is-invalid'); // Ajoute une classe d'erreur pour un style visuel
            errorElement.textContent = "Veuillez entrer une heure valide entre 00:00 et 23:59.";
            return false;
        } else {
            input.classList.remove('is-invalid'); // Supprime la classe d'erreur si la valeur est correcte
            errorElement.textContent = ""; // Efface le message d'erreur
            return true;
        }
    }

    timeInputs.forEach(function (input) {
        Inputmask("99:99", {
            placeholder: "HH:MM",
            insertMode: false,
            showMaskOnHover: false
        }).mask(input);

        input.addEventListener('blur', function () {
            // Valider l'entrée et empêcher le focus de quitter le champ si l'entrée est invalide
            if (!validateTimeInput(this)) {
                this.focus(); // Garde le focus sur le champ si l'heure est invalide
            }
        });

        input.addEventListener('input', function () {
            validateTimeInput(this);
        });
    });
});

// *************** masque de saisi pour l'heure est validation du masque fin ***************

// *************** masque de saisi pour le prix de l'heure validation du masque début ***************
$(document).ready(function () {
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
// *************** masque de saisi pour le prix de l'heure validation du masque fin ***************