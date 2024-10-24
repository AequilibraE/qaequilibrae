document.addEventListener("DOMContentLoaded", function () {
    // Seleciona todos os botões toggle
    var toggleButtons = document.querySelectorAll(".toggle-btn");

    toggleButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            // Alterna a visibilidade da sub-lista relacionada
            var subList = this.nextElementSibling.nextElementSibling;
            if (subList.style.display === "none" || subList.style.display === "") {
                subList.style.display = "block"; // Mostra a sub-lista
                this.textContent = "-"; // Muda o símbolo do botão
            } else {
                subList.style.display = "none"; // Esconde a sub-lista
                this.textContent = "+"; // Muda o símbolo do botão
            }
        });
    });
});
