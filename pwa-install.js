(() => {
  if (!("serviceWorker" in navigator)) return;

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js", { scope: "./" })
      .catch(error => console.warn("SmartHub offline support unavailable:", error));
  });

  let installPrompt = null;
  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    installPrompt = event;
    if (document.getElementById("smarthub-install-button")) return;

    const button = document.createElement("button");
    button.id = "smarthub-install-button";
    button.type = "button";
    button.textContent = "تثبيت التطبيق";
    button.setAttribute("aria-label", "تثبيت SmartHub AI على الجهاز");
    Object.assign(button.style, {
      position: "fixed", insetInlineEnd: "16px", bottom: "16px", zIndex: "9999",
      padding: "12px 18px", border: "1px solid #c8aaff", borderRadius: "12px",
      background: "#7041c2", color: "#fff", font: "700 14px Tajawal, sans-serif",
      boxShadow: "0 8px 24px #0005"
    });
    button.addEventListener("click", async () => {
      if (!installPrompt) return;
      installPrompt.prompt();
      await installPrompt.userChoice;
      installPrompt = null;
      button.remove();
    });
    document.body.appendChild(button);
  });

  window.addEventListener("appinstalled", () => {
    document.getElementById("smarthub-install-button")?.remove();
    installPrompt = null;
  });
})();
