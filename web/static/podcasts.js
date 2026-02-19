(function () {
    "use strict";

    // Handle audio loading errors — show a friendly message instead of a broken player
    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll(".podcast-player audio").forEach(function (audio) {
            audio.addEventListener("error", function () {
                var player = audio.closest(".podcast-player");
                player.innerHTML =
                    '<p class="audio-unavailable">Audio file not yet available. ' +
                    "Regenerate the episode to create the audio.</p>";
            });
        });
    });

    window.toggleRename = function (btn) {
        var card = btn.closest(".podcast-card");
        var display = card.querySelector(".podcast-name-display");
        var edit = card.querySelector(".podcast-rename-edit");
        var toggleBtn = card.querySelector(".btn-rename-toggle");

        if (edit.style.display === "none") {
            edit.style.display = "block";
            display.style.display = "none";
            toggleBtn.style.display = "none";
            var input = edit.querySelector(".rename-input");
            input.focus();
            input.select();
        } else {
            cancelRename(card.querySelector(".rename-actions .btn-secondary"));
        }
    };

    window.saveRename = async function (btn) {
        var card = btn.closest(".podcast-card");
        var episode = card.dataset.episode;
        var input = card.querySelector(".rename-input");
        var display = card.querySelector(".podcast-name-display");
        var edit = card.querySelector(".podcast-rename-edit");
        var toggleBtn = card.querySelector(".btn-rename-toggle");
        var name = input.value.trim();

        btn.textContent = "Saving...";
        btn.disabled = true;

        try {
            var res = await fetch(
                "/api/podcast-name/" + encodeURIComponent(episode),
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name: name }),
                }
            );

            if (!res.ok) {
                throw new Error("Save failed: " + res.status);
            }

            display.textContent = name || episode;
            edit.style.display = "none";
            display.style.display = "";
            toggleBtn.style.display = "";

            // Show or hide the episode ID subtitle
            var idEl = card.querySelector(".podcast-episode-id");
            if (name && name !== episode) {
                if (!idEl) {
                    idEl = document.createElement("p");
                    idEl.className = "podcast-episode-id";
                    var titleArea = card.querySelector(".podcast-title-area");
                    var dateEl = titleArea.querySelector(".date");
                    titleArea.insertBefore(idEl, dateEl);
                }
                idEl.textContent = episode;
                idEl.style.display = "";
            } else if (idEl) {
                idEl.style.display = "none";
            }
        } catch (err) {
            alert("Failed to save name: " + err.message);
        } finally {
            btn.textContent = "Save";
            btn.disabled = false;
        }
    };

    window.cancelRename = function (btn) {
        var card = btn.closest(".podcast-card");
        var display = card.querySelector(".podcast-name-display");
        var edit = card.querySelector(".podcast-rename-edit");
        var input = card.querySelector(".rename-input");
        var toggleBtn = card.querySelector(".btn-rename-toggle");

        input.value = display.textContent;
        edit.style.display = "none";
        display.style.display = "";
        toggleBtn.style.display = "";
    };
})();
