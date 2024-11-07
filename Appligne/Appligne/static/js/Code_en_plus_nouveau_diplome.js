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
            // re-ordonner les ID et les Paramètre des fonctions
            ReOrderId();
        }
    }
// ****************************  pour plusieur pages   fin  ***********************


    // ***************** http://localhost:8000/accounts/nouveai_diplome  debut ****************
    // Fonction pour ajouter un diplôme
    function ajouterDiplome_01(className, options) {
        // Récupérer les options depuis l'attribut de données
        var options = document.getElementById('boutonAjouterDiplome').dataset.options;
        // liste des class des div des diplomes
        var listDiv = document.getElementsByClassName(className);
        // le compte de la liste des class des div des diplomes
        var indice = listDiv.length;

        // Code HTML du nouveau diplôme
        var nouveauDiplomeHTML = `
        <div class="${className}  " id="supprimerDivDiplome_${indice+1}">
                    <div class="col-md-1  position-relative">
                        
                        <input class="form-check-input" type="checkbox" id="principal_id_${indice+1}" name="principal_${indice+1}" >
                        <label class="form-label" for="principal_id_${indice+1}">Principal</label>
                    </div>
                    <div class="col-md-3 col-sm-12 position-relative">
                        <label for="diplome_id_-${indice+1}" class="form-label">Diplôme</label>
                        <select class="form-select" id="diplome_id_${indice+1}" required name="diplome_${indice+1}" >
                        ${options}
                        <option value="Autre">Autre</option>
                        </select>
                    </div>
                    <div id="autreDiplome_${indice+1}" style="display: none;" class="col-md-3 col-sm-12 position-relative div-autre-diplome">
                    <label  class="form-label">Autre diplôme</label>
                    <input type="text" class="form-control form-control-autre" id="autre_diplome_input_${indice+1}" name="autre_diplome_${indice+1}">
                </div>
                    <div class="col-md-2 col-sm-12 position-relative">
                        <label for="date_id_${indice+1}" class="form-label">Optenu</label>
                        <input type="text" class="form-control form-control-date" id="date_id_${indice+1}" required  name="date_obtenu_${indice+1}" placeholder="Sélectionnez une date" >
                    </div>
                    <div class="col-lg-3 col-md-3 col-sm-12 position-relative">
                        <label for="intitule_id_${indice+1}" class="form-label">Intitulé</label>
                        <div class="row">
                            <div class="col-lg-10 col-md-6 col-sm-6 position-relative">
                                <input type="text" class="form-control form-control-intitule" id="intitule_id_${indice+1}"   name="intitule_${indice+1}" >
                            </div>
                            <div class="col-lg-2 col-md-6 col-sm-6 position-relative ">
                                <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivDiplome_${indice+1}')">
                                    <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" viewBox="0 0 26 26">
                                        <path
                                            d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z">
                                        </path>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
        `;

        // Créer un élément div temporaire
        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = nouveauDiplomeHTML;

        // Insérer le nouveau div=nouveauDiplomeHTML juste après le div donc id='boutonAjouterDiplome'
        var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterDiplome');
        boutonAjouterDiplomeDiv.insertAdjacentHTML('beforebegin', nouveauDiplomeHTML);

        // Ajoute un écouteur d'événements au changement de la sélection dans le menu déroulant
        document.getElementById('diplome_id_' + (indice+1)).addEventListener('change', function() {
            // Récupère la valeur sélectionnée dans le menu déroulant
            var selectedValue = this.value;
            // Récupère l'élément div qui contient le champ de saisie pour "Autre diplôme"
            var autreDiplomeDiv = document.getElementById('autreDiplome_' + (indice+1));

            // Vérifie si la valeur sélectionnée est "autre"
            if (selectedValue === 'Autre') {
                // Si oui, affiche le champ de saisie pour "Autre diplôme"
                autreDiplomeDiv.style.display = 'block';
            } else {
                // Sinon, cache le champ de saisie pour "Autre diplôme"
                autreDiplomeDiv.style.display = 'none';
            }
        });

        // re-ordonner les ID et les Paramètre des fonctions
        ReOrderId();

    }
    // ***************** http://localhost:8000/accounts/nouveai_diplome  fin ****************

   // ***********************   http://localhost:8000/accounts/nouveau_diplome    debut  *************************
   function ReOrderId() {
    // liste des class des div des diplomes
    var listDiv = document.getElementsByClassName("row ajout-dipl");

    for (var i = 0; i < listDiv.length; i++) {
        // pour renomer ID du DIV
        var newId = "supprimerDivDiplome_" + (i + 1);
        listDiv[i].id = newId;

        // pour sélectionner le bouton dans le DIV
        var button = listDiv[i].querySelector("button");
        // pour redéfinir l'attribut onclick du bouton sélectionné
        button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

        // pour sélectionner le select dans le DIV
        var select = listDiv[i].querySelector("select");
        // pour renomer ID du select
        var newSelectId = "diplome_id_" + (i + 1);
        select.id = newSelectId;
        select.setAttribute("name", "diplome_" + (i + 1)); // Mettre à jour l'attribut name également si nécessaire

        // Pour sélectionner les inputs avec la classe spécifiée : "form-control form-control-date"
        var dateInputs = listDiv[i].getElementsByClassName("form-control form-control-date");
        for (var j = 0; j < dateInputs.length; j++) {
            // Mettre à jour les attributs id et name des inputs
            var newDateInputId = "date_id_" + (i + 1 );
            dateInputs[j].id = newDateInputId;
            dateInputs[j].setAttribute("name", "date_obtenu_" + (i + 1 ));
            configurerPikaday(i+1)
        }

        // Pour sélectionner les inputs avec la classe spécifiée : "form-check-input"
        var principalInputs = listDiv[i].getElementsByClassName("form-check-input");
        for (var k = 0; k < principalInputs.length; k++) {
            // Mettre à jour les attributs id et name des inputs
            var newPrincipalInputId = "principal_id_" + (i + 1);
            principalInputs[k].id = newPrincipalInputId;
            principalInputs[k].setAttribute("name", "principal_" + (i + 1));
        }

        // Pour sélectionner les inputs avec la classe spécifiée : "form-control form-control-intitule"
        var intituleInputs = listDiv[i].getElementsByClassName("form-control form-control-intitule");
        for (var l = 0; l < intituleInputs.length; l++) {
            // Mettre à jour les attributs id et name des inputs
            var newIntituleInputId = "intitule_id_" + (i + 1);
            intituleInputs[l].id = newIntituleInputId;
            intituleInputs[l].setAttribute("name", "intitule_" + (i + 1));
        }

        //***************** Définir Autre Diplomes comme option   début **************
        // Pour sélectionner le div avec la classe spécifiée : "col-md-3 col-sm-12 position-relative div-autre-diplome"
        var intituledivs = listDiv[i].getElementsByClassName("col-md-3 col-sm-12 position-relative div-autre-diplome");
        for (var l = 0; l < intituledivs.length; l++) {
            // Mettre à jour les attributs id du div
            var newIntituledivstId = "autreDiplome_" + (i + 1);
            intituledivs[l].id = newIntituledivstId;
        }

        
        // Pour sélectionner les inputs avec la classe spécifiée : "form-control form-control-autre"
        var intituleInputs = listDiv[i].getElementsByClassName("form-control form-control-autre");
        for (var l = 0; l < intituleInputs.length; l++) {
            // Mettre à jour les attributs id et name des inputs
            var newIntituleInputId = "autre_diplome_input_" + (i + 1);
            intituleInputs[l].id = newIntituleInputId;
            intituleInputs[l].setAttribute("name", "autre_diplome_" + (i + 1));

            // Ajoute un écouteur d'événements au changement de la sélection dans le menu déroulant
            document.getElementById('diplome_id_' + (i + 1)).addEventListener('change', function() {
                // Récupère la valeur sélectionnée dans le menu déroulant
                var selectedValue = this.value;
                // Récupère l'élément div qui contient le champ de saisie pour "Autre diplôme"
                var autreDiplomeDiv = document.getElementById('autreDiplome_' + (i + 1));

                // Vérifie si la valeur sélectionnée est "autre"
                if (selectedValue === 'Autre') {
                    // Si oui, affiche le champ de saisie pour "Autre diplôme"
                    autreDiplomeDiv.style.display = 'block';
                } else {
                    // Sinon, cache le champ de saisie pour "Autre diplôme"
                    autreDiplomeDiv.style.display = 'none';
                }
            });
        }
    }
}


//***************** Définir Autre Diplomes comme option AU D2MARRAGE DE LA PAGE  début **************
// Ajoute un écouteur d'événements au changement de la sélection dans le menu déroulant
document.getElementById('diplome_id_1').addEventListener('change', function() {
    // Récupère la valeur sélectionnée dans le menu déroulant
    var selectedValue = this.value;
    // Récupère l'élément div qui contient le champ de saisie pour "Autre diplôme"
    var autreDiplomeDiv = document.getElementById('autreDiplome_1');

    // Vérifie si la valeur sélectionnée est "autre"
    if (selectedValue === 'Autre') {
        // Si oui, affiche le champ de saisie pour "Autre diplôme"
        autreDiplomeDiv.style.display = 'block';
    } else {
        // Sinon, cache le champ de saisie pour "Autre diplôme"
        autreDiplomeDiv.style.display = 'none';
    }
});

//***************** Définir Autre Diplomes comme option   Fin **************/
