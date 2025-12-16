// Android-style splash timing
window.addEventListener("load", () => {
    setTimeout(() => {
        document.querySelector(".splash").classList.add("exit");
    }, 3000); // show splash for 3 seconds

    setTimeout(() => {
        window.location.href = "/home/";
    }, 3800); // redirect after fade-out
});
