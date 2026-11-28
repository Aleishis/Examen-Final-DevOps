
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("form-crear-categoria");
    const inputImagenes = document.getElementById("imagenes-tarjetas");
    const rejilla = document.getElementById("rejilla-tarjetas-nuevas");
    const contador = document.getElementById("contador-tarjetas-nuevas");
    const mensaje = document.getElementById("mensaje-tarjetas-nuevas");
    const metadata = document.getElementById("tarjetas-metadata");

    if (
        !form ||
        !inputImagenes ||
        !rejilla ||
        !contador ||
        !mensaje ||
        !metadata
    ) {
        return;
    }

    const MAX_TARJETAS = 50;
    let tarjetas = [];
    let portadaIndex = null;

    function nombreDesdeArchivo(filename) {
        const nombre = filename.split(/[\\/]/).pop();
        const punto = nombre.lastIndexOf(".");

        return (punto > 0 ? nombre.slice(0, punto) : nombre).trim();
    }

    function renderizarTarjetas() {
        tarjetas.forEach(tarjeta => {
            if (tarjeta.previewUrl) {
                URL.revokeObjectURL(tarjeta.previewUrl);
            }
        });

        rejilla.replaceChildren();

        tarjetas.forEach((tarjeta, index) => {
            const article = document.createElement("article");
            article.className = "pareja-tarjeta";

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

            const botonPortada = document.createElement("button");
            botonPortada.type = "button";
            botonPortada.className = "boton";

            function actualizarBotonPortada() {
                const esPortada = portadaIndex === index;
                botonPortada.textContent = esPortada
                    ? "★ Portada seleccionada"
                    : "☆ Designar portada";

                botonPortada.setAttribute(
                    "aria-pressed",
                    String(esPortada)
                );
            }

            botonPortada.addEventListener("click", () => {
                portadaIndex = index;
                renderizarTarjetas();
            });

            actualizarBotonPortada();

            const botonEliminar = document.createElement("button");
            botonEliminar.type = "button";
            botonEliminar.className = "boton boton-eliminar";
            botonEliminar.textContent = "Quitar tarjeta";

            botonEliminar.addEventListener("click", () => {
                tarjetas.splice(index, 1);

                if (portadaIndex === index) {
                    portadaIndex = null;
                } else if (portadaIndex !== null && portadaIndex > index) {
                    portadaIndex--;
                }

                renderizarTarjetas();
            });

            acciones.append(botonPortada, botonEliminar);
            article.append(imagen, formularioNombre, acciones);
            rejilla.appendChild(article);
        });

        contador.textContent = tarjetas.length;

        mensaje.textContent = tarjetas.length
            ? `Tienes ${tarjetas.length} tarjeta(s) preparadas.`
            : "Todavía no has seleccionado imágenes.";

        actualizarMetadata();
    }

    function actualizarMetadata() {
        metadata.value = JSON.stringify({
            tarjetas: tarjetas.map(tarjeta => ({
                nombre: tarjeta.nombre
            })),
            portada_index: portadaIndex
        });
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

        // Permite volver a seleccionar un mismo archivo si se desea.
        inputImagenes.value = "";
        renderizarTarjetas();
    });

    form.addEventListener("submit", event => {
        const nombresValidos = tarjetas.every(tarjeta => {
            const nombre = tarjeta.nombre.trim();
            return nombre.length > 0 && nombre.length <= 100;
        });

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
