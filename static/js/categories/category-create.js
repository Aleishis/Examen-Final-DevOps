
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("form-crear-categoria");
    const inputImagenes = document.getElementById("imagenes-tarjetas");
    const rejilla = document.getElementById("rejilla-tarjetas-nuevas");
    const contador = document.getElementById("contador-tarjetas-nuevas");
    const contadorResumen = document.getElementById("resumen-contador-tarjetas");
    const mensaje = document.getElementById("mensaje-tarjetas-nuevas");
    const metadata = document.getElementById("tarjetas-metadata");
    const inputActiva = document.getElementById("activa");
    const estadoActual = document.getElementById("estado-actual");

    const dificultades = {
        facil: document.getElementById("dificultad-facil"),
        media: document.getElementById("dificultad-media"),
        dificil: document.getElementById("dificultad-dificil")
    };

    if (
        !form ||
        !inputImagenes ||
        !rejilla ||
        !contador ||
        !contadorResumen ||
        !mensaje ||
        !metadata ||
        !inputActiva ||
        !estadoActual
    ) {
        return;
    }

    const MAX_TARJETAS = 50;
    const TARJETAS_POR_DIFICULTAD = 9;

    let tarjetas = [];
    let portadaIndex = null;

    function nombreDesdeArchivo(filename) {
        const nombre = filename.split(/[\\/]/).pop();
        const punto = nombre.lastIndexOf(".");

        return (punto > 0 ? nombre.slice(0, punto) : nombre).trim();
    }


    function actualizarEstadoYDificultades() {
        const cantidad = tarjetas.length;
        const puedeActivarse = cantidad >= 9;

        // No permitir activar la categoría si tiene menos de 9 tarjetas.
        inputActiva.disabled = !puedeActivarse;

        if (!puedeActivarse) {
            inputActiva.checked = false;
        }

        const activa = inputActiva.checked;

        estadoActual.textContent = activa ? "Activa" : "Inactiva";
        estadoActual.classList.toggle("activa", activa);
        estadoActual.classList.toggle("inactiva", !activa);

        dificultades.facil?.classList.toggle("bloqueada", cantidad < 9);
        dificultades.media?.classList.toggle("bloqueada", cantidad < 15);
        dificultades.dificil?.classList.toggle("bloqueada", cantidad < 25);
    }


    inputActiva.addEventListener("change", () => {
        actualizarEstadoYDificultades();
    });



    function actualizarMetadata() {
        metadata.value = JSON.stringify({
            tarjetas: tarjetas.map(tarjeta => ({
                nombre: tarjeta.nombre.trim()
            })),
            portada_index: portadaIndex
        });
    }

    function renderizarTarjetas() {
        tarjetas.forEach(tarjeta => {
            if (tarjeta.previewUrl) {
                URL.revokeObjectURL(tarjeta.previewUrl);
                tarjeta.previewUrl = null;
            }
        });

        rejilla.replaceChildren();

        tarjetas.forEach((tarjeta, index) => {
            const article = document.createElement("article");
            article.className = "pareja-tarjeta tarjeta-nueva";

            const imagen = document.createElement("img");
            imagen.className = "pareja-imagen";
            imagen.src = URL.createObjectURL(tarjeta.file);
            imagen.alt = tarjeta.nombre || "Vista previa de tarjeta";
            imagen.loading = "lazy";
            tarjeta.previewUrl = imagen.src;

            const formularioNombre = document.createElement("div");
            formularioNombre.className = "formulario-nombre-tarjeta";

            const inputNombre = document.createElement("input");
            inputNombre.type = "text";
            inputNombre.value = tarjeta.nombre;
            inputNombre.maxLength = 100;
            inputNombre.required = true;
            inputNombre.setAttribute(
                "aria-label",
                `Nombre de la tarjeta ${index + 1}`
            );

            inputNombre.addEventListener("input", () => {
                tarjeta.nombre = inputNombre.value;
                imagen.alt = tarjeta.nombre || "Vista previa de tarjeta";
                actualizarMetadata();
            });

            formularioNombre.appendChild(inputNombre);

            const acciones = document.createElement("div");
            acciones.className = "acciones-pareja";

            const selectorPortada = document.createElement("label");
            selectorPortada.className = "selector-portada";
            selectorPortada.title = "Seleccionar portada";

            const inputPortada = document.createElement("input");
            inputPortada.type = "radio";
            inputPortada.name = "portada_visual";
            inputPortada.value = String(index);
            inputPortada.checked = portadaIndex === index;
            inputPortada.setAttribute(
                "aria-label",
                `Designar ${tarjeta.nombre || `tarjeta ${index + 1}`} como portada`
            );

            const textoPortada = document.createElement("span");
            textoPortada.textContent =
                portadaIndex === index ? "♛ Portada" : "♛ Designar portada";

            inputPortada.addEventListener("change", () => {
                portadaIndex = index;
                renderizarTarjetas();
            });

            selectorPortada.append(inputPortada, textoPortada);

            const botonEliminar = document.createElement("button");
            botonEliminar.type = "button";
            botonEliminar.className = "boton boton-eliminar";
            botonEliminar.textContent = "Quitar tarjeta";

            botonEliminar.addEventListener("click", () => {
                const tarjetaEliminada = tarjetas[index];

                if (tarjetaEliminada.previewUrl) {
                    URL.revokeObjectURL(tarjetaEliminada.previewUrl);
                }

                tarjetas.splice(index, 1);

                if (portadaIndex === index) {
                    portadaIndex = null;
                } else if (portadaIndex !== null && portadaIndex > index) {
                    portadaIndex--;
                }

                renderizarTarjetas();
            });

            acciones.append(selectorPortada, botonEliminar);
            article.append(imagen, formularioNombre, acciones);
            rejilla.appendChild(article);
        });

        contador.textContent = tarjetas.length;
        contadorResumen.textContent = tarjetas.length;

        mensaje.textContent = tarjetas.length
            ? `Tienes ${tarjetas.length} tarjeta(s) preparadas.`
            : "Todavía no has seleccionado imágenes.";

        actualizarEstadoYDificultades();
        actualizarMetadata();
    }

    inputImagenes.addEventListener("change", () => {
        const archivos = Array.from(inputImagenes.files || []);
        const disponibles = MAX_TARJETAS - tarjetas.length;

        if (archivos.length > disponibles) {
            mensaje.textContent =
                `Solo puedes agregar ${disponibles} tarjeta(s) más.`;
        }

        archivos.slice(0, disponibles).forEach(file => {
            tarjetas.push({
                file,
                nombre: nombreDesdeArchivo(file.name),
                previewUrl: null
            });
        });

        inputImagenes.value = "";
        renderizarTarjetas();
    });

    form.addEventListener("submit", event => {
        const nombreCategoria = document
            .getElementById("nombre")
            .value.trim();

        const nombresValidos = tarjetas.every(tarjeta => {
            const nombre = tarjeta.nombre.trim();
            return nombre.length > 0 && nombre.length <= 100;
        });

        if (!nombreCategoria || nombreCategoria.length > 100) {
            event.preventDefault();
            mensaje.textContent =
                "Escribe un nombre de categoría de hasta 100 caracteres.";
            return;
        }

        if (tarjetas.length > MAX_TARJETAS || !nombresValidos) {
            event.preventDefault();
            mensaje.textContent =
                "Revisa los nombres: deben tener entre 1 y 100 caracteres, " +
                "y no puedes superar las 50 tarjetas.";
            return;
        }

        const dataTransfer = new DataTransfer();

        tarjetas.forEach(tarjeta => {
            dataTransfer.items.add(tarjeta.file);
        });

        inputImagenes.files = dataTransfer.files;

        metadata.value = JSON.stringify({
            tarjetas: tarjetas.map(tarjeta => ({
                nombre: tarjeta.nombre.trim()
            })),
            portada_index: portadaIndex
        });
    });

    renderizarTarjetas();
});
