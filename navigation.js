(() => {
  const pages = ["home", "tools", "assistant", "account", "about"];
  const pageTitles = {
    home: "الرئيسية",
    tools: "الأدوات",
    assistant: "المساعد الذكي",
    account: "الحساب والدعم",
    about: "عن المنصة"
  };

  function showPage(id, updateHistory = false) {
    if (!pages.includes(id)) id = "home";

    pages.forEach((pageId) => {
      const page = document.getElementById(pageId);
      if (page) {
        page.hidden = pageId !== id;
        page.classList.toggle("page-active", pageId === id);
      }
    });

    document.querySelectorAll(".side-link").forEach((link) => {
      const active = link.getAttribute("href") === "#" + id;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });

    document.title = pageTitles[id] + " | SmartHub AI";
    if (updateHistory && location.hash !== "#" + id) {
      history.pushState({ page: id }, "", "#" + id);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  document.addEventListener("click", (event) => {
    const link = event.target.closest('a[href^="#"]');
    if (!link) return;
    const id = link.getAttribute("href").slice(1);
    if (!pages.includes(id)) return;
    event.preventDefault();
    showPage(id, true);
  });

  window.addEventListener("popstate", () => {
    showPage(location.hash.slice(1) || "home");
  });

  window.addEventListener("hashchange", () => {
    showPage(location.hash.slice(1) || "home");
  });

  showPage(location.hash.slice(1) || "home");
})();