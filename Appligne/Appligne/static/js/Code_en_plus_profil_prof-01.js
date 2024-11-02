
// Fonction pour redimensionner les textarea selon leur contenu
function adjustTextareaHeight() {
    const textareas = document.getElementsByClassName('form-control profil');

    for (let i = 0; i < textareas.length; i++) {
        const textarea = textareas[i];
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight - 2) + 'px';
    }
}

// Combine les deux onload et DOMContentLoaded dans une seule fonction
window.onload = function() {
    adjustTextareaHeight(); // Redimensionne les textarea
};

document.addEventListener("DOMContentLoaded", function() {
    // Redimensionne les textarea sur input
    document.addEventListener('input', adjustTextareaHeight);
});
