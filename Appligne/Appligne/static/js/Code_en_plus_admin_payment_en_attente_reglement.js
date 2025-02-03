// date class="form-control-date" début
// Charger les scripts Pikaday et Inputmask dynamiquement

$(function() {
    $.datepicker.regional['fr'] = {
		closeText: 'Fermer',
		prevText: '&#x3c;Préc',
		nextText: 'Suiv&#x3e;',
		currentText: 'Aujourd\'hui',
		monthNames: ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
		'Juillet','Aout','Septembre','Octobre','Novembre','Decembre'],
		monthNamesShort: ['Jan','Fev','Mar','Avr','Mai','Jun',
		'Jul','Aou','Sep','Oct','Nov','Dec'],
		dayNames: ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'],
		dayNamesShort: ['Dim','Lun','Mar','Mer','Jeu','Ven','Sam'],
		dayNamesMin: ['Di','Lu','Ma','Me','Je','Ve','Sa'],
		weekHeader: 'Sm',
		dateFormat: 'dd-mm-yy',
		firstDay: 1,
		isRTL: false,
		showMonthAfterYear: false,
		yearSuffix: '',
		// minDate: 0,
		// maxDate: '+12M +0D',
		numberOfMonths: 1,
		showButtonPanel: true
		};
	$.datepicker.setDefaults($.datepicker.regional['fr']);
    $(".form-control-date").datepicker({
        dateFormat: "dd/mm/yy"
    });
    // Appliquer Inputmask pour empêcher la saisie incorrecte
    $(input).inputmask("99/99/9999", { placeholder: "JJ/MM/AAAA" });
});

// Fonction pour valider si une date est correcte au format DD/MM/YYYY
function isValidDate(dateStr) {
    let regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    let match = dateStr.match(regex);
    
    if (!match) return false; // Vérifie le format

    let day = parseInt(match[1], 10);
    let month = parseInt(match[2], 10);
    let year = parseInt(match[3], 10);

    let dateObj = new Date(year, month - 1, day);

    return (
        dateObj.getFullYear() === year &&
        dateObj.getMonth() + 1 === month &&
        dateObj.getDate() === day
    );
}

// Ajouter un événement pour vérifier la date lors de la saisie ou perte de focus
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".form-control-date").forEach(function (input) {
        input.addEventListener("blur", function () {
            let dateValue = input.value.trim();
            let errorMessage = input.nextElementSibling; // Recherche un élément d'erreur existant

            if (!isValidDate(dateValue)) {
                if (!errorMessage || !errorMessage.classList.contains("date-error")) {
                    errorMessage = document.createElement("small");
                    errorMessage.classList.add("date-error");
                    errorMessage.style.color = "red";
                    errorMessage.textContent = "Veuillez entrer une date valide (DD/MM/YYYY)";
                    input.parentNode.appendChild(errorMessage);
                }
            } else {
                if (errorMessage) {
                    errorMessage.remove(); // Supprime le message d'erreur si la date est correcte
                }
            }
        });
    });
});
