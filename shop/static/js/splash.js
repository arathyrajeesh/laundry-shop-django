window.addEventListener("load", () => {
    const splash = document.querySelector(".splash-container");

    // Phase 1: Start the exit animation after 2.5 seconds
    // (Total visible time: 2.5s + 0.8s fade out = 3.3s)
    setTimeout(() => {
        if (splash) {
            splash.classList.add("exit");
        }
    }, 2500); 

    // Phase 2: Redirect once the fade-out is complete
    setTimeout(() => {
        window.location.href = "/home/";
    }, 3300); 
});