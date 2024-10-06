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
            var field = document.getElementById('date_id_' + indice);
            field.value = formattedDate;
            
            // Trouver le prochain champ de date et lui donner le focus
            var nextField = document.querySelector(`#date_id_${indice + 1}`);
            if (nextField) {
                nextField.focus();
            } else {
                // Si aucun champ suivant n'est trouvé, vous pouvez également le déplacer ailleurs
                // Par exemple, vous pouvez déplacer le focus au premier champ d'heure ou autre champ
                var firstTimeField = document.querySelector('.form-control-heure');
                if (firstTimeField) {
                    firstTimeField.focus();
                }
            }
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
            configurerPikaday(i+1)
            
        }   
    });
    //*******************************  ClassName("form-control form-control-date") fin *********************************** */


// ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome
    // function supprimerDiv(divId) {
    //     var div = document.getElementById(divId);
    //     if (div) {
    //         div.parentNode.removeChild(div);
    //         // re-ordonner les ID et les Paramètre des fonctions
    //         ReOrderId02();
    //     }
    // }
// ****************************  pour plusieur pages   debut  ***********************

document.addEventListener("DOMContentLoaded", function() {
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

    timeInputs.forEach(function(input) {
        Inputmask("99:99", {
            placeholder: "HH:MM",
            insertMode: false,
            showMaskOnHover: false
        }).mask(input);

        input.addEventListener('blur', function() {
            // Valider l'entrée et empêcher le focus de quitter le champ si l'entrée est invalide
            if (!validateTimeInput(this)) {
                this.focus(); // Garde le focus sur le champ si l'heure est invalide
            }
        });

        input.addEventListener('input', function() {
            validateTimeInput(this);
        });
    });
});

// *************** masque de saisi pour l'heure est validation du masque fin ***************
