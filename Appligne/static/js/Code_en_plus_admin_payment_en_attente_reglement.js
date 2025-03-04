// Gestion des checkboxes
document.addEventListener("DOMContentLoaded", function () {
    const checkboxTous = document.getElementById("checkbox_tous_id");
    const checkboxes = document.querySelectorAll(".checkbox_tous");

    if (checkboxTous) {
        checkboxTous.addEventListener("change", function () {
            checkboxes.forEach(checkbox => {
                checkbox.checked = checkboxTous.checked;
            });
        });

        checkboxes.forEach(checkbox => {
            checkbox.addEventListener("change", function () {
                if (!this.checked) {
                    checkboxTous.checked = false;
                } else if ([...checkboxes].every(cb => cb.checked)) {
                    checkboxTous.checked = true;
                }
            });
        });
    }
});

// Datepicker et Inputmask
$(function () {
    $.datepicker.regional['fr'] = {
        closeText: 'Fermer',
        prevText: '&#x3c;Préc',
        nextText: 'Suiv&#x3e;',
        currentText: 'Aujourd\'hui',
        monthNames: ['Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
            'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'],
        monthNamesShort: ['Jan', 'Fev', 'Mar', 'Avr', 'Mai', 'Jun',
            'Jul', 'Aou', 'Sep', 'Oct', 'Nov', 'Dec'],
        dayNames: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
        dayNamesShort: ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'],
        dayNamesMin: ['Di', 'Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa'],
        weekHeader: 'Sm',
        dateFormat: 'dd-mm-yy',
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: '',
        numberOfMonths: 1,
        showButtonPanel: true
    };
    $.datepicker.setDefaults($.datepicker.regional['fr']);

    $(".form-control-date").attr("autocomplete", "off").datepicker({
        dateFormat: "dd/mm/yy"
    });

    $("input.form-control-date").inputmask("99/99/9999", { placeholder: "JJ/MM/AAAA" });
});

// Fonction pour valider une date
function isValidDate(dateStr) {
    let regex = /^(\d{2})\/(\d{2})\/(\d{4})$/;
    let match = dateStr.match(regex);

    if (!match) return false;

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

// Vérification de la date lors de la saisie
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".form-control-date").forEach(function (input) {
        input.addEventListener("blur", function () {
            let dateValue = input.value.trim();
            let errorMessage = input.nextElementSibling;

            if (!isValidDate(dateValue)) {
                if (!errorMessage || !errorMessage.classList.contains("date-error")) {
                    errorMessage = document.createElement("small");
                    errorMessage.classList.add("date-error");
                    errorMessage.style.color = "red";
                    errorMessage.textContent = "Veuillez entrer une date valide (JJ/MM/AAAA)";
                    input.parentNode.appendChild(errorMessage);
                }
            } else {
                if (errorMessage) {
                    errorMessage.remove();
                }
            }
        });
    });
});
