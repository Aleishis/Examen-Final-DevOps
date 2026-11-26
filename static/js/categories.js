const casillas = document.querySelectorAll(".seleccion-categoria");
const botonEliminar = document.querySelector(".boton-eliminar");

    function actualizarSeleccion() {
        const seleccionadas = document.querySelectorAll(
            ".seleccion-categoria:checked"
        ).length;

        botonEliminar.textContent =
            `Borrar categorías (${seleccionadas})`;

        botonEliminar.disabled = seleccionadas === 0;
    }

    casillas.forEach(casilla => {
        casilla.addEventListener("change", actualizarSeleccion);
    });
    

    document.querySelectorAll(".tarjeta-clicable").forEach(tarjeta => {
        tarjeta.addEventListener("click", event => {
            // No navegar al interactuar con controles de la tarjeta.
            if (event.target.closest("input, label, a, button, select")) {
                return;
            }

            window.location.href = tarjeta.dataset.url;
        });

        tarjeta.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                // Evitar desplazarse al presionar la barra espaciadora.
                event.preventDefault();
                window.location.href = tarjeta.dataset.url;
            }
        });
    });
