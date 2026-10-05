/* Editor de lecciones con Quill: sincroniza el HTML con el formulario y sube imágenes. */
(function () {
  "use strict";

  var contenedor = document.getElementById("editor-leccion");
  if (!contenedor || typeof Quill === "undefined") {
    return;
  }
  var campo = document.getElementById(contenedor.dataset.campo);
  var urlImagen = contenedor.dataset.urlImagen;
  var csrf = document.querySelector("input[name=csrfmiddlewaretoken]").value;
  var aviso = document.getElementById("editor-aviso");

  function mostrarAviso(texto, tipo) {
    aviso.textContent = texto;
    aviso.className = "alert alert-" + tipo + " small py-2 mt-2";
    aviso.hidden = !texto;
  }

  function subirImagen() {
    var selector = document.createElement("input");
    selector.type = "file";
    selector.accept = "image/png,image/jpeg,image/gif";
    selector.addEventListener("change", function () {
      var archivo = selector.files[0];
      if (!archivo) {
        return;
      }
      var datos = new FormData();
      datos.append("imagen", archivo);
      mostrarAviso("Subiendo imagen…", "info");
      fetch(urlImagen, {
        method: "POST",
        body: datos,
        headers: { "X-CSRFToken": csrf },
        credentials: "same-origin"
      })
        .then(function (respuesta) {
          return respuesta.json().then(function (cuerpo) {
            return { ok: respuesta.ok, cuerpo: cuerpo };
          });
        })
        .then(function (resultado) {
          if (!resultado.ok) {
            throw new Error(resultado.cuerpo.error || "No se pudo subir la imagen.");
          }
          var rango = editor.getSelection(true);
          editor.insertEmbed(rango.index, "image", resultado.cuerpo.url, "user");
          mostrarAviso("", "info");
        })
        .catch(function (error) {
          mostrarAviso(error.message, "danger");
        });
    });
    selector.click();
  }

  var editor = new Quill(contenedor, {
    theme: "snow",
    placeholder: "Escriba el contenido de la lección…",
    modules: {
      toolbar: {
        container: [
          [{ header: [2, 3, false] }],
          ["bold", "italic", "underline", "strike"],
          [{ list: "ordered" }, { list: "bullet" }],
          ["blockquote", "link", "image"],
          ["clean"]
        ],
        handlers: { image: subirImagen }
      }
    }
  });

  if (campo.value) {
    editor.clipboard.dangerouslyPasteHTML(campo.value);
  }

  contenedor.closest("form").addEventListener("submit", function () {
    campo.value = editor.getLength() > 1 ? editor.getSemanticHTML() : "";
  });
})();
