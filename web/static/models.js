(function () {
    "use strict";

    window.toggleNotes = function (btn) {
        var card = btn.closest(".model-notes");
        var display = card.querySelector(".notes-display");
        var edit = card.querySelector(".notes-edit");

        if (edit.style.display === "none") {
            edit.style.display = "block";
            display.style.display = "none";
            btn.textContent = "Cancel";
        } else {
            cancelNotes(card.querySelector(".notes-actions .btn-secondary"));
        }
    };

    window.saveNotes = async function (btn) {
        var card = btn.closest(".model-notes");
        var slug = card.dataset.slug;
        var textarea = card.querySelector(".notes-textarea");
        var display = card.querySelector(".notes-display");
        var edit = card.querySelector(".notes-edit");
        var toggleBtn = card.querySelector(".btn-notes-toggle");
        var text = textarea.value.trim();

        card.classList.add("notes-saving");
        btn.textContent = "Saving...";

        try {
            var res = await fetch("/api/models/" + encodeURIComponent(slug) + "/notes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text }),
            });

            if (!res.ok) {
                throw new Error("Save failed: " + res.status);
            }

            if (text) {
                display.textContent = text;
                display.classList.remove("notes-empty");
            } else {
                display.textContent = "Click Edit to add notes...";
                display.classList.add("notes-empty");
            }

            edit.style.display = "none";
            display.style.display = "block";
            toggleBtn.textContent = "Edit";
        } catch (err) {
            alert("Failed to save notes: " + err.message);
            btn.textContent = "Save";
        } finally {
            card.classList.remove("notes-saving");
        }
    };

    window.cancelNotes = function (btn) {
        var card = btn.closest(".model-notes");
        var display = card.querySelector(".notes-display");
        var edit = card.querySelector(".notes-edit");
        var textarea = card.querySelector(".notes-textarea");
        var toggleBtn = card.querySelector(".btn-notes-toggle");

        var currentText = display.classList.contains("notes-empty") ? "" : display.textContent;
        textarea.value = currentText;

        edit.style.display = "none";
        display.style.display = "block";
        toggleBtn.textContent = "Edit";
    };
})();
