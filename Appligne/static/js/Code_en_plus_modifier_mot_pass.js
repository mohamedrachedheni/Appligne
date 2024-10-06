/**
 * Toggle the visibility of a password input field and change the icon accordingly.
 *
 * @param {string} fieldId - The ID of the password input field to toggle.
 */
function togglePassword(fieldId) {
    // Récupère le champ de mot de passe et l'icône associée
    var field = document.getElementById(fieldId);
    var icon = field.nextElementSibling.querySelector('i');

    // Bascule entre les types "password" et "text" pour afficher ou masquer le mot de passe
    if (field.type === "password") {
        field.type = "text";
        // Change l'icône pour indiquer que le mot de passe est visible
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        field.type = "password";
        // Change l'icône pour indiquer que le mot de passe est masqué
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}
