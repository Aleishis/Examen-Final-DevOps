
document.addEventListener("DOMContentLoaded", () => {
    // Selección de tarjetas
    const checkboxes = document.querySelectorAll(".checkbox-pareja");
    const seleccionarTodas = document.getElementById(
        "seleccionar-todas-parejas"
    );
    const contador = document.getElementById("contador-seleccionadas");
    const botonEliminar = document.getElementById(
        "boton-eliminar-seleccionadas"
    );
    const formularioEliminar = document.getElementById(
        "form-eliminar-seleccionadas"
    );

    function actualizarSeleccion() {
        let cantidadSeleccionadas = 0;

        checkboxes.forEach(checkbox => {
            const tarjeta = checkbox.closest(".pareja-tarjeta");

            if (checkbox.checked) {
                cantidadSeleccionadas++;
                tarjeta?.classList.add("seleccionada");
            } else {
                tarjeta?.classList.remove("seleccionada");
            }
        });

        if (contador) {
            contador.textContent = cantidadSeleccionadas;
        }

        if (botonEliminar) {
            botonEliminar.disabled = cantidadSeleccionadas === 0;

            botonEliminar.textContent = cantidadSeleccionadas > 0
                ? `Eliminar seleccionadas (${cantidadSeleccionadas})`
                : "Eliminar seleccionadas";
        }

        if (seleccionarTodas) {
            seleccionarTodas.checked =
                checkboxes.length > 0 &&
                cantidadSeleccionadas === checkboxes.length;

            seleccionarTodas.indeterminate =
                cantidadSeleccionadas > 0 &&
                cantidadSeleccionadas < checkboxes.length;

            seleccionarTodas.disabled = checkboxes.length === 0;
        }
    }

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener("change", actualizarSeleccion);
    });

    if (seleccionarTodas) {
        seleccionarTodas.addEventListener("change", () => {
            checkboxes.forEach(checkbox => {
                checkbox.checked = seleccionarTodas.checked;
            });

            actualizarSeleccion();
        });
    }

    if (formularioEliminar) {
        formularioEliminar.addEventListener("submit", event => {
            const cantidad = document.querySelectorAll(
                ".checkbox-pareja:checked"
            ).length;

            if (cantidad === 0) {
                event.preventDefault();
                return;
            }

            const confirmar = window.confirm(
                `¿Eliminar las ${cantidad} tarjetas seleccionadas? ` +
                "Esta acción no se puede deshacer."
            );

            if (!confirmar) {
                event.preventDefault();
            }
        });
    }

    actualizarSeleccion();

    // Guardado automático del nombre de las tarjetas
    document.querySelectorAll(
        ".formulario-nombre-tarjeta input[name='nombre']"
    ).forEach(input => {
        let nombreOriginal = input.value;

        input.addEventListener("change", () => {
            const nombreNuevo = input.value.trim();

            if (nombreNuevo !== "" && nombreNuevo !== nombreOriginal) {
                input.form.requestSubmit();
            }
        });
    });
});
