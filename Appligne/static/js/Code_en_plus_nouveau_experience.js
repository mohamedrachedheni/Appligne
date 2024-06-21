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


// ********************************   http://localhost:8000/accounts/nouveau_experience   debut ***********
    // http://localhost:8000/accounts/nouveau_experience
    // Dans le cas Nouvelles Expériences Professeur avec deux dates début et
    function ReOrderId02() {
        // liste des class des div des diplomes
        var listDiv = document.getElementsByClassName("row  ajout-exper");

        for (var i = 0; i < listDiv.length; i++) {
            // pour renomer ID du DIV
            var newId = "supprimer_div_" + (i + 1);
            listDiv[i].id = newId;

            // pour sélectionner le bouton dans le DIV
            var button = listDiv[i].querySelector("button");
            // pour redéfinir l'attribut onclick du bouton sélectionné
            button.setAttribute("onclick", "supprimerDiv('" + newId + "')");

            // pour sélectionner le select dans le DIV
            var select = listDiv[i].querySelector("select");
            // pour renomer ID du select
            var newSelectId = "type_id_" + (i + 1);
            select.id = newSelectId;
            select.setAttribute("name", "type_" + (i + 1)); // Mettre à jour l'attribut name également si nécessaire

            // Pour sélectionner les inputs avec la classe spécifiée : "form-control form-control-date"
            var dateInputs = listDiv[i].getElementsByClassName("form-control form-control-date");
            for (var j = 0; j < dateInputs.length; j++) {
                // Mettre à jour les attributs id et name des inputs
                // dans le cas ou il y a deux dates dans le meme DIV
                var newDateInputId = "date_id_" + (2*i + 1 + j);
                dateInputs[j].id = newDateInputId;
                if (j === 0) { dateInputs[j].setAttribute("name", "date_debut_" + (2*i + 1 + j));
                configurerPikaday(2*i + 1 );
                }
                if (j === 1) { dateInputs[j].setAttribute("name", "date_fin_" + (2*i + 1 + j)); 
                configurerPikaday(2*i + 2);
                }
            
            }

            // Pour sélectionner les inputs avec la classe spécifiée : "form-check-input check-pricipal"
            var principalInputs = listDiv[i].getElementsByClassName("form-check-input check-pricipal");
            for (var k = 0; k < principalInputs.length; k++) {
                // Mettre à jour les attributs id et name des inputs
                var newPrincipalInputId = "principal_id_" + (i + 1);
                principalInputs[k].id = newPrincipalInputId;
                principalInputs[k].setAttribute("name", "principal_" + (i + 1));
            }

            // Pour sélectionner les inputs avec la classe spécifiée : "form-check-input mg-checkbox"
            var principalInputs = listDiv[i].getElementsByClassName("form-check-input mg-checkbox");
            for (var k = 0; k < principalInputs.length; k++) {
                // Mettre à jour les attributs id et name des inputs
                var newPrincipalInputId = "act_id_" + (i + 1);
                principalInputs[k].id = newPrincipalInputId;
                principalInputs[k].setAttribute("name", "act_" + (i + 1));
            }

            // Pour sélectionner les inputs avec la classe spécifiée : "form-control form-control-comm"
            var intituleInputs = listDiv[i].getElementsByClassName("form-control form-control-comm");
            for (var l = 0; l < intituleInputs.length; l++) {
                // Mettre à jour les attributs id et name des inputs
                var newIntituleInputId = "comm_id_" + (i + 1);
                intituleInputs[l].id = newIntituleInputId;
                intituleInputs[l].setAttribute("name", "comm_" + (i + 1));
            }
            
        }
    }
// ********************************   http://localhost:8000/accounts/nouveau_experience   fin ***********





// ********************************   http://localhost:8000/accounts/nouveau_experience   debut ***********
    // http://localhost:8000/accounts/creer_compte_prof
    // Fonction pour ajouter une expérience
    function ajouterExperience(className) {
            
        // liste des class des div des diplomes
        var listDiv = document.getElementsByClassName(className);
        // le compte de la liste des class des div des diplomes
        var indice = listDiv.length;

        // Code HTML du nouveau diplôme
        var nouveauDiplomeHTML = `
        <div class="${className} p-3" id="supprimer_div_${indice+1}">
                    <div class="col-lg-1 col-md-2 col-sm-2 position-relative">
                        <label class="form-label" >Principal</label>
                        <input class="form-check-input check-pricipal" type="checkbox"  id="principal_${indice+1}" name="principal_${indice+1}" >
                    </div>
                    <div class="col-lg-3 col-md-10 col-sm-10 position-relative">
                        <label class="form-label">Type</label>
                        <select class="form-select" id="type_id_${indice+1}" required name="type_${indice+1}" >
                            <option>Auteur(e)  d'ouvrages scolaires</option>
                            <option>Chargé(e) d'eneignement</option>
                            <option>Chargé(e) de TD à l'université</option>
                            <option>Correcteur / Correctrice</option>
                            <option>Enseignant(e) chercheur(euse)</option>
                            <option>Formateur / Formatrice</option>
                            <option>Jury</option>
                            <option>Khôlleur(euse) en CPGE</option>
                            <option>Maître de conférences</option>
                            <option>Professeur(e) à l'université</option>
                            <option>Professeur(e) de l'éducation nationale</option>
                            <option>Professeur(e) en CPGE</option>
                            <option>Professeur(e) en grande école</option>
                            <option>Professeur(e) enstage intensif</option>
                            <option>Professeur(e) indépendant</option>
                            <option>Titeur / Tutrice à l'université</option>
                        </select>
                    </div>
                    <div class="col-lg-2 col-md-6 col-sm-6 position-relative">
                        <label class="form-label">Début</label>
                        <input type="text" class="form-control form-control-date" id="date_id_${((indice+1)*2)-1}"  required name="date_debut_${((indice+1)*2)-1}" >
                    </div>
                    <div class="col-lg-2 col-md-6 col-sm-6 position-relative">
                        <label class="form-label">Fin</label>
                        <input type="text" class="form-control form-control-date" id="date_id_${(indice+1)*2}" name="date_fin_${(indice+1)*2}" >
                    </div>
                    <div class="col-lg-2 col-md-4 col-sm-6 g-3 ">
                        <div class="row ">
                            <div class="col-12" style="padding: -25px; margin-top: -8px;">
                                <label class="form-check-label" >Actuellement</label>

                            </div>
                            <div class="col-12" style="padding: 15px; padding-left: 45px;">
                                <div class="form-check form-switch switch-column">
                                    <input class="form-check-input mg-checkbox" type="checkbox" role="switch"
                                        id="act_id_${indice+1}" checked onchange="toggleText()"
                                        style="padding-right: -5px;" name="act_${indice+1}" >
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-2 col-md-8 col-sm-6 position-relative" style="margin-left: -40px; ">
                        <label class="form-label">Commentaires</label>
                        <div class="row" style="margin-right:-100px">
                            <div class="col-lg-8 col-md-6 col-sm-6 position-relative">
                                <input type="text" class="form-control" id="comm_id_${indice+1}" name="comm_${indice+1}" >
                            </div>
                            <div class="col-lg-4 col-md-6 col-sm-6 position-relative">
                                <button class="btn  btn-sup " onclick="supprimerDiv('supprimer_div_${indice+1}')">
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
        var boutonAjouterDiplomeDiv = document.getElementById('bouton_ajout_div');
        boutonAjouterDiplomeDiv.insertAdjacentHTML('beforebegin', nouveauDiplomeHTML);

        // re-ordonner les ID et les Paramètre des fonctions
        ReOrderId02();

    }
// ********************************   http://localhost:8000/accounts/nouveau_experience   fin ***********










// ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome
    function supprimerDiv(divId) {
        var div = document.getElementById(divId);
        if (div) {
            div.parentNode.removeChild(div);
            // re-ordonner les ID et les Paramètre des fonctions
            ReOrderId02();
        }
    }
// ****************************  pour plusieur pages   debut  ***********************

