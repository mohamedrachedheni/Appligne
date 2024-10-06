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