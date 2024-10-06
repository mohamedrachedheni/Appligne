/* &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&   début  &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& */
    /* nouveau_matiere.htlm */

    // Définir la matière sélectionnée par Ajouter l'attribut selected
    // le paramètre selector est par défaut = 'matiere_id_1'
    function addChangeListener(selector = 'matiere_id_1') {
        // le selecteur dont id=selector
        const selectElement = document.querySelector('#'+selector);
        // quant l'évennement sur changement est déclanché
        selectElement.addEventListener('change', function(event) {
        //  récupérer la première option sélectionnée
        const selectedOption = this.selectedOptions[0];
        // si il y a une option selectionnée
        if (selectedOption) {
            selectedOption.setAttribute('selected', 'selected'); // Ajouter l'attribut selected
        }
        // pour tous options non selectionnées
        const options = Array.from(this.querySelectorAll('option'));
        options.forEach(option => {
            if (option !== selectedOption) {
                // Supprimez l'attribut selected           
                option.removeAttribute('selected'); // Supprimer l'attribut selected
            }
        });
        });
    }


/*  oui */
// fonction réservée au moment du chargement de la page
// pour donner le code JS pour l'option matiére si elle est sélectionnée
// en donnant l'attribut selected
document.addEventListener('DOMContentLoaded', function() {
    // Appel de la fonction sans paramètre, utilise le sélecteur par défaut
    addChangeListener();
});


    /*  oui */
    /* sélectionnez les optios dans un premier select et les ajouter dans un autre */
    /* et rendre les options sélectionnées dans le premier select non visibles et désactivées, ou vice-versa, */ 
    /*en réorganisant les options dans le deuxième select par ID de manière croissant*/
    /* Les paramaitres près définis: .btn-ajouter_1; .btn-enlever_1; #niveau_id_1; #niveau_chx_id_1 */

    // Définition de la fonction générique pour sélectionner les niveaux du premier select vers le deuxième
    function gestionSelection(indice = 1) {
        // Sélecteurs pour le premier select de la liste de tous les niveaux
        // et le second select des niveaux choisis
        var selecteurPremier = "#niveau_id_" + indice;
        var selecteurSecond = "niveau_chx_id_" + indice;
        
        // Lorsque le bouton "ajouter" est cliqué
        // les options sélectionnées deviennent non visible dans le premier select et passent au deuxième select

        $(document).on('click', ".btn-ajouter_" + indice, function() {
            // Récupérez les options sélectionnées dans le premier select
            var selectedOptions = $(selecteurPremier + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOption = $(this).clone(); // Clone l'option sélectionnée
                var selectedOptionId = selectedOption.attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // rendre l'attribut de l'option selectionnée: selected
                selectedOption.attr('selected', 'selected');

                // Ajoute l'option au second select
                $('#' + selecteurSecond).append(selectedOption);

                // Change le contenu du name de l'option ajoutée pour correspondre à son ID
                //selectedOption.attr('name', selectedOptionId);

                // Réorganisez les options dans le deuxième select par leur ID
                sortOptionsById(selecteurSecond);
                
                // Rendre non visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', true).hide();
            });
        });

        /* oui */
    // Fonction pour réorganiser les options par leur ID par ordre croissant
    function sortOptionsById(selectId) {
        var select = $("#" + selectId);
        var options = select.find("option");

        options.sort(function(a, b) {
            return parseInt(a.id.split("_").pop()) - parseInt(b.id.split("_").pop());
        });

        select.html(options);
    }

        // Lorsque le bouton "enlever" est cliqué
        // les options sélectionnées dans le deuxième select sont
        // supprimées et deviennent visible dans le premier sélect
        $(document).on('click', ".btn-enlever_" + indice, function() {
            // Récupérez les options sélectionnées dans le second select
            var selectedOptions = $('#' + selecteurSecond + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOptionId = $(this).attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // Rend visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', false).show();

                $(this).remove(); // Supprime l'option du second select
            });
        });

        // Lorsque le bouton "enlever" est cliqué
        // les options sélectionnées dans le deuxième select sont
        // supprimées et deviennent visible dans le premier sélect
        $(document).on('click', ".btn-enlever_" + indice, function() {
            // Récupérez les options sélectionnées dans le second select
            var selectedOptions = $('#' + selecteurSecond + " option:selected");

            // Parcours de chaque option sélectionnée
            selectedOptions.each(function() {
                var selectedOptionId = $(this).attr('id'); // Récupère l'ID de l'option sélectionnée
                
                // Rend visible l'option avec le même ID dans le premier select
                $(selecteurPremier + " option[id='" + selectedOptionId + "']").prop('disabled', false).show();

                $(this).remove(); // Supprime l'option du second select
            });
        });
    }


    /*  oui */
    // Attendez que le DOM soit complètement chargé
    // Pour sélectionner les options du premier sélect vers le deuxième
    // au chargement de la page avec le paramètre par défaut (indice = 1)
    $(document).ready(function() {
        // Appel de la fonction générique avec le paramètre par défaut
        // elle est réservée au moment du chargement des pages web
        gestionSelection();
    });

    /*  oui */
    // Récupération du formulaire
    var formNouvelleMatiere = document.getElementById('formNouvelleMatiere');

    function selectNiveauxById(indice = 1) {

        // Ajout d'un écouteur d'événements pour l'événement de soumission du formulaire
        formNouvelleMatiere.addEventListener('submit', function(event) {
            
            // Récupération du menu déroulant (select)
            var selectNiveau = document.getElementById('niveau_chx_id_' + indice);

            // Sélection de toutes les options dans le menu déroulant
            for(var i = 0; i < selectNiveau.options.length; i++) {
                selectNiveau.options[i].selected = true;
            }
        });
    };
    /*  oui */
    // Ajout d'un écouteur d'événements pour l'événement de soumission du formulaire
    // avec le paramère par défaut indice=1 au chargement de la page
    // fonction réservée à l'évennement juste avant le moment du soumission du formulaire au submit
    // lorsque le bouton type="submit" est cliqué (name="btn_eng")
    // pour sélectionner tous les options du deuxième select
    document.addEventListener('DOMContentLoaded', function() {
        // Appel de la fonction sans paramètre, utilise le sélecteur par défaut
        selectNiveauxById();
    });


    // Fonction pour ajouter le DIV d'une nouvelle matière à enseigner
    function ajouterMatiere(className, className2) {
        //pour définir un nouveai indice qui est le max des des 
        //indices existant dans la page plus un
        // pour éviter le dédoublement des ID est des name et des class
        // liste des class des div des matières
        var listDiv = document.getElementsByClassName(className);
        var indice = 0;
        
        // calcule de l'indice maximum
        for (var i = 0; i < listDiv.length; i++){
            var str = listDiv[i].id.replace("supprimerDivMatiere-", "");
            var code = parseInt(str);
            if (code > indice) {indice = code};
        };
        
        // Code HTML du nouveau diplôme
        var nouveauDiplomeHTML = `
                <div class="${className}" id="supprimerDivMatiere-${indice+1}">
                    <div class="col-md-1  position-relative">

                        
                        <input class="form-check-input" type="checkbox"  id="principal_id_${indice+1}" name="principal_${indice+1}">
                        <label class="form-label" >Principal</label>
                        
                    </div>
                    <div class=" col-lg-9  position-relative">
                        <label class="form-label">Matières</label>
                        <select class="form-select select-matiere" id="matiere_id_${indice+1}" required name="matiere_${indice+1}">

                            <optgroup label="Enseignements scientifiques">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_110" selected disabled>Sélectionnez une matière</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_111 " >Chimie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_112 " >Dessin industriel</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_113 " >Electronique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_114 " >Informatique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_115 " >Logique maths</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_116 " >Maths</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_117 " >NSI</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_118 " >Physique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_119 " >Physique-chimie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_1110 " >Sciences de l'ingénieurs</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_1111 " >Statistique</option>
                            </optgroup>

                            <optgroup label="Lettres">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_121 " >Français</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_122 " >Grec</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_123 " >Latin</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_124 " >Orthographe</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_125 " >Synthèse de document</option>
                            </optgroup>

                            <optgroup label="Langues vivantes">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_131 " >Allemand</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_132 " >Anglais</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_133 " >Arabe</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_134 " >Chinois</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_135 " >Coréen</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_136 " >Espagnol</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_137 " >FLE</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_138 " >Italien</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_139 " >Japonais</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_1310 " >Portugais</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_1311 " >Russe</option>
                            </optgroup>
                            <optgroup label="Sciences humaines">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_141 " >Culture générale</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_142 " >Education civique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_143 " >ESH</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_144 " >Géopolitique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_145 " >Histoire - Géographie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_146 " >Humanites litérature philosophie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_147 " >Management</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_148 " >Philosophie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_149 " >Sciences politiques</option>
                            </optgroup>
                            <optgroup label="Economie">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_151 " >Comptabilité</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_152 " >Control de gestion</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_153 " >Droit</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_154 " >Economie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_155 " >Fiscalité</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_156 " >Gestion financière</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_157 " >Macroéconomie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_158 " >Marketing</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_159 " >Microéconomie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_1510 " >SES</option>
                            </optgroup>
                            <optgroup label="Sciences naturelles">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_161 " >Anatomie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_162 " >Biologie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_163 " >Biologie - Ecologie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_164 " >Biochimie</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_165 " >Biophysique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_166 " >Biostatique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_167 " >SVT</option>
                            </optgroup>
                            <optgroup label="Préparation orale">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_171 " >Coaching scolaire</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_172 " >Entretien de motivation</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_173 " >Grand oral du bac</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_174 " >Orientation scolaire</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_175 " >TIPE</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_176 " >TPE</option>
                            </optgroup>
                            <optgroup label="Enseignements artistiques">
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_181 " >Art du cirque</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_182 " >Arts plastiques</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_183 " >Cinéma audiovisuel</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_184 " >Danse</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_185 " >Histoire des arts</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_186 " >Musique</option>
                                <option class="option-matiere" id="opt_mat_div_${indice+1}_id_187 " >Théatre</option>
                            </optgroup>
                        </select>
                    </div>
                    <div class="col-lg-2 position-relative p-2 g-4">
                        <button class="btn  btn-sup " onclick="supprimerDiv('supprimerDivMatiere-${indice+1}')">
                            <svg xmlns="http://www.w3.org/2000/svg" x="0px" y="0px" viewBox="0 0 26 26">
                                <path
                                    d="M 11.5 -0.03125 C 9.542969 -0.03125 7.96875 1.59375 7.96875 3.5625 L 7.96875 4 L 4 4 C 3.449219 4 3 4.449219 3 5 L 3 6 L 2 6 L 2 8 L 4 8 L 4 23 C 4 24.644531 5.355469 26 7 26 L 19 26 C 20.644531 26 22 24.644531 22 23 L 22 8 L 24 8 L 24 6 L 23 6 L 23 5 C 23 4.449219 22.550781 4 22 4 L 18.03125 4 L 18.03125 3.5625 C 18.03125 1.59375 16.457031 -0.03125 14.5 -0.03125 Z M 11.5 2.03125 L 14.5 2.03125 C 15.304688 2.03125 15.96875 2.6875 15.96875 3.5625 L 15.96875 4 L 10.03125 4 L 10.03125 3.5625 C 10.03125 2.6875 10.695313 2.03125 11.5 2.03125 Z M 6 8 L 11.125 8 C 11.25 8.011719 11.371094 8.03125 11.5 8.03125 L 14.5 8.03125 C 14.628906 8.03125 14.75 8.011719 14.875 8 L 20 8 L 20 23 C 20 23.5625 19.5625 24 19 24 L 7 24 C 6.4375 24 6 23.5625 6 23 Z M 8 10 L 8 22 L 10 22 L 10 10 Z M 12 10 L 12 22 L 14 22 L 14 10 Z M 16 10 L 16 22 L 18 22 L 18 10 Z">
                                </path>
                            </svg>
                        </button>
                    </div>
                    <div class=" col-md-6  position-relative">
                        <label for="validationTooltipNiv1" class="form-label">Niveaux (Sélectionnez un ou plusieurs
                            niveaux)</label>
                            <select class="form-select select-niveau" id="niveau_id_${indice+1}"  multiple>
                            <optgroup label="Collège" >
                                <option   id="opt_div_${indice+1}_id_112 " >6ème</option>
                                <option   id="opt_div_${indice+1}_id_113 " >5ème</option>
                                <option   id="opt_div_${indice+1}_id_114 " >4ème</option>
                                <option   id="opt_div_${indice+1}_id_115 " >3ème</option>
                            </optgroup>
                            <optgroup label="Lycée" >
                                <option   id="opt_div_${indice+1}_id_122 " >Seconde</option>
                                <option   id="opt_div_${indice+1}_id_123 " >Première STMGL</option>
                                <option   id="opt_div_${indice+1}_id_124 " >Première STL</option>
                                <option   id="opt_div_${indice+1}_id_125 " >Première Générale</option>
                                <option   id="opt_div_${indice+1}_id_126 " >Première STI2D</option>
                                <option   id="opt_div_${indice+1}_id_127 " >Terminale STMG</option>
                                <option   id="opt_div_${indice+1}_id_128 " >Terminale STI2D</option>
                                <option   id="opt_div_${indice+1}_id_129 " >Terminale Générale</option>
                                <option   id="opt_div_${indice+1}_id_1210">Terminale STL</option>
                            </optgroup>
                            <optgroup label="Concours et prépa" >
                                <option   id="opt_div_${indice+1}_id_131 " >Prépa Concours Geipi Polytech</option>
                                <option   id="opt_div_${indice+1}_id_132 " >Avenir-Puissance Alpha-Advance-Geipi</option>
                                <option   id="opt_div_${indice+1}_id_133 " >Acces-Sésame</option>
                                <option   id="opt_div_${indice+1}_id_134 " >Prépa Concours Avenir</option>
                                <option   id="opt_div_${indice+1}_id_135 " >Prépa Sciences Po</option>
                                <option   id="opt_div_${indice+1}_id_136 " >Prépa Concours ESA</option>
                                <option   id="opt_div_${indice+1}_id_137 " >Prépa Concours Advance</option>
                                <option   id="opt_div_${indice+1}_id_138 " >Prépa Concours Acces</option>
                                <option   id="opt_div_${indice+1}_id_139 " >Prépa Concours CRPE</option>
                                <option   id="opt_div_${indice+1}_id_1310 " >Pass BBA</option>
                                <option   id="opt_div_${indice+1}_id_1311  " >Prépa Concours Puissance Alpha</option>
                                <option   id="opt_div_${indice+1}_id_1312 " >Prépa Concours Sésame</option>
                                <option   id="opt_div_${indice+1}_id_1313 " >Prépa intégrée 1ère année</option>
                            </optgroup>
                            <optgroup label="Autres">
                                <option   id="opt_div_${indice+1}_id_141 " >MP2I</option>
                                <option   id="opt_div_${indice+1}_id_142 " >MPSI</option>
                                <option   id="opt_div_${indice+1}_id_143 " >TSI</option>
                                <option   id="opt_div_${indice+1}_id_144 " >TB</option>
                                <option   id="opt_div_${indice+1}_id_145 " >TBC</option>
                                <option   id="opt_div_${indice+1}_id_146 " >ATS</option>
                                <option   id="opt_div_${indice+1}_id_147 " >PTSI</option>
                                <option   id="opt_div_${indice+1}_id_148 " >BBPST 1</option>
                                <option   id="opt_div_${indice+1}_id_149 " >PCSI</option>
                                <option   id="opt_div_${indice+1}_id_1410 " >Math Sup</option>
                                <option   id="opt_div_${indice+1}_id_1411 " >MP</option>
                                <option   id="opt_div_${indice+1}_id_1412 " >PSI</option>
                                <option   id="opt_div_${indice+1}_id_1413 " >PC</option>
                                <option   id="opt_div_${indice+1}_id_1414 " >Prépa intégré 2ème année</option>
                                <option   id="opt_div_${indice+1}_id_1415 " >TSI 2</option>
                                <option   id="opt_div_${indice+1}_id_1416 " >MPI</option>
                                <option   id="opt_div_${indice+1}_id_1417 " >PT</option>
                                <option   id="opt_div_${indice+1}_id_1418 " >BCPST 2</option>
                                <option   id="opt_div_${indice+1}_id_1419 " >Maths Spé</option>
                                <option   id="opt_div_${indice+1}_id_1420 " >ECG 1</option>
                                <option   id="opt_div_${indice+1}_id_1421 " >D1 ENS Cachan</option>
                                <option   id="opt_div_${indice+1}_id_1422 " >Hypokhâgne ALL</option>
                                <option   id="opt_div_${indice+1}_id_1423 " >Khâgne AL</option>
                                <option   id="opt_div_${indice+1}_id_1424 " >Khâgne BL</option>
                                <option   id="opt_div_${indice+1}_id_1425 " >Gei Univ</option>
                                <option   id="opt_div_${indice+1}_id_1426 " >CAST Ing</option>
                                <option   id="opt_div_${indice+1}_id_1427 " >TOEIC</option>
                                <option   id="opt_div_${indice+1}_id_1428 " >Tage Mage</option>
                                <option   id="opt_div_${indice+1}_id_1429 " >GMAT</option>
                                <option   id="opt_div_${indice+1}_id_1430 " >Score IAE Message</option>
                                <option   id="opt_div_${indice+1}_id_1431 " >TOEFL</option>
                                <option   id="opt_div_${indice+1}_id_1432 " >Architechture</option>
                                <option   id="opt_div_${indice+1}_id_1433 " >Infirmier</option>
                                <option   id="opt_div_${indice+1}_id_1434 " >Capes</option>
                                <option   id="opt_div_${indice+1}_id_1435 " >Tage 2</option>
                                <option   id="opt_div_${indice+1}_id_1436 " >IELTS</option>
                                <option   id="opt_div_${indice+1}_id_1437 " >DCG</option>
                                <option   id="opt_div_${indice+1}_id_1438 " >DSCG</option>
                                <option   id="opt_div_${indice+1}_id_1439 " >Agrégation</option>
                                <option   id="opt_div_${indice+1}_id_1440 " >BUT</option>
                                <option   id="opt_div_${indice+1}_id_1441 " >BTS</option>
                                <option   id="opt_div_${indice+1}_id_1442 " >Licence 1</option>
                                <option   id="opt_div_${indice+1}_id_1443 " >Licence 2</option>
                                <option   id="opt_div_${indice+1}_id_1444 " >Licence 3</option>
                                <option   id="opt_div_${indice+1}_id_1445 " >Master 1</option>
                                <option   id="opt_div_${indice+1}_id_1446 " >Master 2</option>
                                <option   id="opt_div_${indice+1}_id_1447 " >Adultes</option>
                            </optgroup>
                        </select>
                    </div>
                    <div class=" col-md-6  position-relative">
                        <label class="form-label">Les niveaux que vous enseignez pour la matière choisie</label>
                        <select class="form-select select-chx" id="niveau_chx_id_${indice+1}" multiple name="niveau_chx_${indice+1}">

                        </select>
                    </div>
                    <div class=" col-md-6  position-relative">
                        <div class="btn  btn-sup btn-ajouter_${indice+1}" id="btn-ajouter_${indice+1}" >
                            <svg class="svg-inline--fa fa-arrow-right" aria-labelledby="svg-inline--fa-title-ajx18rtJBjSu" data-prefix="fa-solid" data-icon="arrow-right" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" data-fa-i2svg=""><title >Submit My Tax Return</title><path fill="currentColor" d="M438.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-160-160c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L338.8 224 32 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l306.7 0L233.4 393.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l160-160z"></path></svg>
                        </div>
                    </div>
                    <div class=" col-md-6  position-relative">
                        <div class="btn btn-sup btn-enlever_${indice+1}" id="btn-enlever_${indice+1}"  >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><!--!Font Awesome Free 6.5.1 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2024 Fonticons, Inc.--><path d="M9.4 233.4c-12.5 12.5-12.5 32.8 0 45.3l160 160c12.5 12.5 32.8 12.5 45.3 0s12.5-32.8 0-45.3L109.2 288 416 288c17.7 0 32-14.3 32-32s-14.3-32-32-32l-306.7 0L214.6 118.6c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0l-160 160z"/></svg>
                        </div>
                    </div>
                </div>`;

        // Créer un élément div temporaire
        var tempDiv = document.createElement('div');
        tempDiv.innerHTML = nouveauDiplomeHTML;

        // Insérer le nouveau diplôme juste après le bouton "Ajouter une matière"
        var boutonAjouterDiplomeDiv = document.getElementById('boutonAjouterMatiere');
        boutonAjouterDiplomeDiv.insertAdjacentHTML('beforebegin', nouveauDiplomeHTML);

        //Lier le code JS au nouveau select des matière
        var str = className2 + (indice+1);
        addChangeListener(str);

        //Lier le code JS au nouveau select des nineaux
        // pour gérer la selection des options entre le select id="niveau_id_${indice+1}" 
        // et le select id="niveau_chx_id_${indice+1}"
        gestionSelection((indice+1));

        // Ajout d'un écouteur d'événements pour l'événement de soumission du formulaire
        // avec le paramère  (indice + 1) au au moment de l'ajout du DIV
        // fonction réservée à l'évennement juste avant le moment du soumission du formulaire au submit
        // lorsque le bouton type="submit" est cliqué (name="btn_eng")
        // pour selectionner tous les options du select id="niveau_chx_id_${indice+1}" 
        selectNiveauxById((indice+1))

        // pour attribuer, au moment de l'ajout du div, le code JS au bouton supprimer pour le div dont id=divId 
        var divId = 'supprimerDivMatiere-'+(indice+1)
        // fonction pour supprimer un champ div pour un diplome 
        function supprimerDiv(divId) {
            var div = document.getElementById(divId);
            if (div) {
                div.parentNode.removeChild(div);
            }
        }

        }

        // ****************************  pour plusieur pages   debut  ***********************
    // fonction pour supprimer un champ div pour un diplome le code JS est attribué au chargement de la page seulement
    function supprimerDiv(divId) {
        var div = document.getElementById(divId);
        if (div) {
            div.parentNode.removeChild(div);
        }
    }
    
// ****************************  pour plusieur pages   debut  ***********************

/* &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&  fin &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& */