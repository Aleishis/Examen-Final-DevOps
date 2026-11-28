
document.addEventListener("DOMContentLoaded", () => {

    // Mostrar mensajes de respuesta en la pantalla.
    function mostrarMensaje(elemento, mensaje, error = false) {

        if (!elemento) {
            return;
        }

        elemento.textContent = mensaje;
        elemento.classList.toggle("message-error", error);
        elemento.classList.toggle("message-success", !error);
    }


    // Leer la respuesta JSON del servidor.
    async function leerRespuesta(response) {

        let datos;

        try {
            datos = await response.json();
        } catch {
            throw new Error("El servidor devolvio una respuesta no valida.");
        }

        if (!response.ok) {
            throw new Error(
                datos.mensaje || "No fue posible completar la operacion."
            );
        }

        return datos;
    }


    // ---------------------------------------------------------------
    // Configuracion de categoria y dificultad
    // ---------------------------------------------------------------

    const configForm = document.getElementById("room-config-form");

    if (configForm) {

        const categorySelect = document.getElementById(
            "category-select"
        );

        const difficultySelect = document.getElementById(
            "difficulty-select"
        );

        const saveButton = document.getElementById("save-config");

        const mensaje = document.getElementById("lobby-message");

        const difficultyLabels = {
            facil: "Facil",
            media: "Media",
            dificil: "Dificil"
        };


        // Actualizar las dificultades segun la categoria seleccionada.
        function actualizarDificultades() {

            const opcionSeleccionada =
                categorySelect.selectedOptions[0];

            const dificultades = (
                opcionSeleccionada.dataset.difficulties || ""
            )
                .split(",")
                .filter(Boolean);

            const dificultadAnterior = difficultySelect.value;

            difficultySelect.replaceChildren();

            dificultades.forEach(dificultad => {

                const option = document.createElement("option");

                option.value = dificultad;
                option.textContent = difficultyLabels[dificultad];

                difficultySelect.appendChild(option);

            });

            if (dificultades.includes(dificultadAnterior)) {

                difficultySelect.value = dificultadAnterior;

            } else if (dificultades.length > 0) {

                difficultySelect.value = dificultades[0];

            }

            saveButton.disabled = dificultades.length === 0;
        }


        // Actualizar dificultades cuando cambia la categoria.
        categorySelect.addEventListener(
            "change",
            actualizarDificultades
        );


        // Guardar la configuracion de la sala.
        configForm.addEventListener("submit", async event => {

            event.preventDefault();

            saveButton.disabled = true;

            try {

                const response = await fetch(
                    configForm.dataset.configUrl,
                    {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        body: JSON.stringify({
                            categoria_id: Number(categorySelect.value),
                            dificultad: difficultySelect.value
                        })
                    }
                );

                const datos = await leerRespuesta(response);

                mostrarMensaje(
                    mensaje,
                    datos.mensaje,
                    false
                );

                // Recargar para mostrar la nueva configuracion.
                window.location.reload();

            } catch (error) {

                mostrarMensaje(
                    mensaje,
                    error.message,
                    true
                );

                saveButton.disabled = false;
            }

        });


        // Cargar las dificultades correspondientes al inicio.
        actualizarDificultades();

    }



    // ---------------------------------------------------------------
    // Entrada a una sala
    // ---------------------------------------------------------------

    document.querySelectorAll("[data-enter-url]").forEach(button => {

        button.addEventListener("click", async () => {

            const salaId = button.dataset.roomId;
            const mensaje = document.getElementById(
                `mensaje-sala-${salaId}`
            );

            button.disabled = true;

            try {

                const response = await fetch(button.dataset.enterUrl, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json"
                    }
                });

                const datos = await leerRespuesta(response);

                mostrarMensaje(
                    mensaje,
                    datos.mensaje,
                    false
                );

                // Ir a la pantalla de espera.
                window.location.assign(button.dataset.lobbyUrl);

            } catch (error) {

                mostrarMensaje(
                    mensaje,
                    error.message,
                    true
                );

                button.disabled = false;
            }

        });

    });


    // ---------------------------------------------------------------
    // Transferencia del anfitrion
    // ---------------------------------------------------------------

    document.querySelectorAll("[data-transfer-url]").forEach(button => {

        button.addEventListener("click", async () => {

            const jugadorId = Number(button.dataset.playerId);
            const url = button.dataset.transferUrl;
            const mensaje = document.getElementById("lobby-message");

            button.disabled = true;

            try {

                const response = await fetch(url, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    body: JSON.stringify({
                        nuevo_anfitrion_id: jugadorId
                    })
                });

                const datos = await leerRespuesta(response);

                mostrarMensaje(
                    mensaje,
                    datos.mensaje,
                    false
                );

                // Actualizar la informacion de los participantes.
                window.location.reload();

            } catch (error) {

                mostrarMensaje(
                    mensaje,
                    error.message,
                    true
                );

                button.disabled = false;
            }

        });

    });


    // ---------------------------------------------------------------
    // Actualizacion del estado de preparacion
    // ---------------------------------------------------------------

    const readyButton = document.getElementById("toggle-ready");

    if (readyButton) {

        readyButton.addEventListener("click", async () => {

            const mensaje = document.getElementById("lobby-message");

            // Obtener el estado actual del jugador.
            const estadoActual =
                readyButton.dataset.currentReady === "true";

            // Invertir el estado actual.
            const nuevoEstado = !estadoActual;

            readyButton.disabled = true;

            try {

                const response = await fetch(
                    readyButton.dataset.readyUrl,
                    {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Content-Type": "application/json",
                            "Accept": "application/json"
                        },
                        body: JSON.stringify({
                            listo: nuevoEstado
                        })
                    }
                );

                const datos = await leerRespuesta(response);

                mostrarMensaje(
                    mensaje,
                    datos.mensaje,
                    false
                );

                // Actualizar la pantalla para mostrar los cambios.
                window.location.reload();

            } catch (error) {

                mostrarMensaje(
                    mensaje,
                    error.message,
                    true
                );

                readyButton.disabled = false;
            }

        });

    }

    // ---------------------------------------------------------------
    // Salida de una sala
    // ---------------------------------------------------------------

    const leaveButton = document.getElementById("leave-room");

    if (leaveButton) {

        leaveButton.addEventListener("click", async () => {

            const confirmar = window.confirm(
                "¿Estas seguro de que deseas abandonar esta sala?"
            );

            if (!confirmar) {
                return;
            }

            const mensaje = document.getElementById("lobby-message");

            leaveButton.disabled = true;

            try {

                const response = await fetch(
                    leaveButton.dataset.exitUrl,
                    {
                        method: "POST",
                        credentials: "same-origin",
                        headers: {
                            "Accept": "application/json"
                        }
                    }
                );

                const datos = await leerRespuesta(response);

                mostrarMensaje(
                    mensaje,
                    datos.mensaje,
                    false
                );

                // Regresar al listado de salas.
                window.location.assign("/salas");

            } catch (error) {

                mostrarMensaje(
                    mensaje,
                    error.message,
                    true
                );

                leaveButton.disabled = false;
            }

        });

    }

});
