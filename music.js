const player = document.getElementById("player");
const label = document.getElementById("nowplaying");
const buttons = [...document.querySelectorAll(".trk")];

function select(button, play) {
    buttons.forEach(b => b.removeAttribute("aria-current"));
    button.setAttribute("aria-current", "true");
    player.src = button.dataset.src;
    label.textContent = "playing " + button.dataset.title;
    if (play) player.play().catch(() => {
        label.textContent = button.dataset.title + " (press play)";
    });
}

buttons.forEach(button => {
    button.addEventListener("click", () => select(button, true));
});

player.addEventListener("ended", () => {
    const current = buttons.findIndex(b => b.hasAttribute("aria-current"));
    const next = buttons[current + 1];
    if (next) select(next, true);
    else label.textContent = "nothing playing";
});

player.addEventListener("pause", () => {
    if (!player.ended && player.src) label.textContent = label.textContent.replace("playing ", "paused ");
});

player.addEventListener("play", () => {
    label.textContent = label.textContent.replace("paused ", "playing ");
});
