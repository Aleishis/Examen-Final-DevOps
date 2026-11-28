document.addEventListener("DOMContentLoaded", () => {

    // ==========================================
    // 1. Selección múltiple de categorías
    // ==========================================

    const casillas = document.querySelectorAll(".seleccion-categoria");
    const botonEliminar = document.querySelector(".boton-eliminar");

    if (casillas.length > 0 && botonEliminar) {

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

        actualizarSeleccion();
    }


    // ==========================================
    // 2. Navegación de tarjetas clicables
    // ==========================================

    document.querySelectorAll(".tarjeta-clicable").forEach(tarjeta => {

        tarjeta.addEventListener("click", event => {
            // No navegar al interactuar con controles.
            if (event.target.closest("input, label, a, button, select")) {
                return;
            }

            window.location.href = tarjeta.dataset.url;
        });

        tarjeta.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                window.location.href = tarjeta.dataset.url;
            }
        });

    });


    // ==========================================
    // 3. Formulario de creación de categoría
    // Vista previa de las imágenes seleccionadas
    // ==========================================

    const selectorImagenes = document.getElementById("imagenes");
    const contenedorParejas = document.getElementById("parejas");
    const contador = document.getElementById("contador");
    const portadaIndice = document.getElementById("portada_indice");
    const formulario = document.getElementById("formulario-categoria");

    // Ejecutar esta funcionalidad únicamente si existe
    // el formulario de creación y todos sus elementos.
    if (
        selectorImagenes &&
        contenedorParejas &&
        contador &&
        portadaIndice &&
        formulario
    ) {

        let urlsTemporales = [];

        selectorImagenes.addEventListener("change", () => {

            // Liberar las URL temporales de la selección anterior.
            urlsTemporales.forEach(url => URL.revokeObjectURL(url));
            urlsTemporales = [];

            contenedorParejas.replaceChildren();
            portadaIndice.value = "";

            const archivos = Array.from(selectorImagenes.files);

            if (archivos.length > 50) {
                alert("Solo puedes seleccionar un máximo de 50 imágenes.");

                selectorImagenes.value = "";
                contador.textContent = "0 / 50 parejas seleccionadas";
                return;
            }

            contador.textContent =
                `${archivos.length} / 50 parejas seleccionadas`;

            archivos.forEach((archivo, indice) => {

                const tarjeta = document.createElement("article");
                tarjeta.className = "pareja-formulario";

                // Vista previa de la imagen.
                const imagen = document.createElement("img");
                const url = URL.createObjectURL(archivo);

                urlsTemporales.push(url);

                imagen.src = url;
                imagen.alt = "Vista previa de " + archivo.name;

                // Campo para el nombre de la pareja.
                const etiquetaNombre = document.createElement("label");
                etiquetaNombre.htmlFor = `nombre-pareja-${indice}`;
                etiquetaNombre.textContent = "Nombre de la pareja";

                const campoNombre = document.createElement("input");
                campoNombre.type = "text";
                campoNombre.id = `nombre-pareja-${indice}`;
                campoNombre.name = "nombres";
                campoNombre.required = true;
                campoNombre.maxLength = 100;

                // Quitar la extensión del archivo.
                campoNombre.value = archivo.name.replace(/\.[^/.]+$/, "");

                // Opción para seleccionar la portada.
                const etiquetaPortada = document.createElement("label");
                etiquetaPortada.className = "elegir-portada";

                const radioPortada = document.createElement("input");
                radioPortada.type = "radio";
                radioPortada.name = "portada_visual";
                radioPortada.value = indice;

                radioPortada.addEventListener("change", () => {
                    portadaIndice.value = indice;
                });

                etiquetaPortada.append(
                    radioPortada,
                    document.createTextNode("Usar como portada")
                );

                tarjeta.append(
                    imagen,
                    etiquetaNombre,
                    campoNombre,
                    etiquetaPortada
                );

                contenedorParejas.appendChild(tarjeta);
            });

        });


        // Validación antes de enviar el formulario.
        formulario.addEventListener("submit", event => {

            if (selectorImagenes.files.length > 50) {
                event.preventDefault();
                alert("No puedes agregar más de 50 parejas.");
                return;
            }

            if (
                selectorImagenes.files.length > 0 &&
                !contenedorParejas.querySelector(
                    'input[name="portada_visual"]:checked'
                )
            ) {
                // La portada es opcional.
                portadaIndice.value = "";
            }

        });

    }

});


/* ==========================================
   Ocultar notificaciones automáticamente
========================================== */

document.querySelectorAll(".mensajes").forEach(mensajes => {
    setTimeout(() => {
        mensajes.classList.add("ocultando");

        setTimeout(() => {
            mensajes.remove();
        }, 400);
    }, 4000);
});


document.addEventListener("DOMContentLoaded", () => {
    const interruptor = document.getElementById("activa");
    const estado = document.getElementById("estado-actual");

    if (!interruptor || !estado) {
        return;
    }

    function actualizarEstado() {
        const activa = interruptor.checked;

        estado.textContent = activa ? "Activa" : "Inactiva";

        estado.classList.toggle("activa", activa);
        estado.classList.toggle("inactiva", !activa);
    }

    interruptor.addEventListener("change", actualizarEstado);
    actualizarEstado();
});

