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
