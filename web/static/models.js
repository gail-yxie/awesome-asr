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

    // ── Generate Podcast & Mind Map ──

    window.generateMedia = async function (btn) {
        var arxivId = btn.dataset.arxiv;
        var card = btn.closest(".model-card");
        var progressEl = card.querySelector(".generate-progress");
        var linksEl = card.querySelector(".model-links");

        btn.disabled = true;
        btn.textContent = "Generating...";
        progressEl.style.display = "block";
        progressEl.innerHTML = "";

        try {
            var res = await fetch("/api/models/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ arxiv_id: arxivId }),
            });

            if (!res.ok) throw new Error("Server error: " + res.status);

            var reader = res.body.getReader();
            var decoder = new TextDecoder();
            var buffer = "";
            var result = null;

            while (true) {
                var chunk = await reader.read();
                if (chunk.done) break;
                buffer += decoder.decode(chunk.value, { stream: true });

                var lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i].trim();
                    if (!line.startsWith("data: ")) continue;
                    try {
                        var event = JSON.parse(line.substring(6));
                        if (event.type === "progress") {
                            // Mark previous step as done
                            var prev = progressEl.querySelector(".gen-step:last-child");
                            if (prev) prev.classList.add("done");
                            var step = document.createElement("div");
                            step.className = "gen-step";
                            step.textContent = event.label;
                            progressEl.appendChild(step);
                        } else if (event.type === "done") {
                            // Mark last step done
                            var last = progressEl.querySelector(".gen-step:last-child");
                            if (last) last.classList.add("done");
                            result = event;
                        } else if (event.type === "error") {
                            result = { error: event.message };
                        }
                    } catch (e) { /* skip malformed */ }
                }
            }

            if (!result) throw new Error("No response received");
            if (result.error) throw new Error(result.error);

            // Replace Generate button with Podcast/Mind Map buttons
            btn.remove();
            if (result.urls.podcast_url) {
                var a = document.createElement("a");
                a.href = result.urls.podcast_url;
                a.className = "btn btn-podcast btn-sm";
                a.target = "_blank";
                a.textContent = "Podcast";
                linksEl.appendChild(a);
            }
            if (result.urls.mindmap_url) {
                var a = document.createElement("a");
                a.href = result.urls.mindmap_url;
                a.className = "btn btn-mindmap btn-sm";
                a.target = "_blank";
                a.textContent = "Mind Map";
                linksEl.appendChild(a);
            }

            // Clear progress after a moment
            setTimeout(function () {
                progressEl.style.display = "none";
                progressEl.innerHTML = "";
            }, 2000);

        } catch (err) {
            var errEl = document.createElement("div");
            errEl.className = "gen-error";
            errEl.textContent = "Error: " + err.message;
            progressEl.appendChild(errEl);
            btn.disabled = false;
            btn.textContent = "Generate Podcast & Mind Map";
        }
    };
})();
