(function () {
  "use strict";

  var doc = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var hasGSAP = Boolean(window.gsap && window.ScrollTrigger);
  var motion = !reduce && hasGSAP;

  if (!motion) {
    doc.classList.remove("motion");
  }

  var head = document.querySelector(".site-head");
  var onHeadScroll = function () {
    if (head) head.classList.toggle("is-scrolled", window.scrollY > 8);
  };
  window.addEventListener("scroll", onHeadScroll, { passive: true });
  onHeadScroll();

  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      var command = button.closest(".cmd");
      var code = command ? command.querySelector("code") : null;
      if (!code || !navigator.clipboard) return;
      navigator.clipboard.writeText(code.textContent.trim()).then(function () {
        var original = button.textContent;
        button.textContent = "Copied";
        button.classList.add("is-copied");
        window.setTimeout(function () {
          button.textContent = original;
          button.classList.remove("is-copied");
        }, 1600);
      }).catch(function () {
        button.textContent = "Select";
      });
    });
  });

  var citeDemo = document.querySelector(".cite-demo");
  var citeButton = citeDemo ? citeDemo.querySelector(".cite") : null;
  if (citeDemo && citeButton) {
    citeButton.addEventListener("click", function () {
      var open = citeDemo.classList.toggle("is-open");
      citeButton.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape" || !citeDemo.classList.contains("is-open")) return;
      citeDemo.classList.remove("is-open");
      citeButton.setAttribute("aria-expanded", "false");
      citeButton.focus();
    });
  }

  var tocLinks = Array.prototype.slice.call(document.querySelectorAll(".toc a"));
  if (tocLinks.length && "IntersectionObserver" in window) {
    var tocSections = tocLinks.map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    }).filter(Boolean);

    var tocObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        tocLinks.forEach(function (link) {
          link.classList.toggle("is-active", link.getAttribute("href") === "#" + entry.target.id);
        });
      });
    }, { rootMargin: "-24% 0px -64% 0px", threshold: 0 });

    tocSections.forEach(function (section) {
      tocObserver.observe(section);
    });
  }

  if (!motion) {
    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function (event) {
        if (link.classList.contains("skip")) return;
        var target = document.querySelector(link.getAttribute("href"));
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: "auto", block: "start" });
      });
    });
    return;
  }

  window.gsap.registerPlugin(window.ScrollTrigger);

  var lenis = null;
  if (window.Lenis) {
    lenis = new window.Lenis({ duration: 1.05, smoothWheel: true });
    lenis.on("scroll", window.ScrollTrigger.update);
    window.gsap.ticker.add(function (time) {
      lenis.raf(time * 1000);
    });
    window.gsap.ticker.lagSmoothing(0);
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (link.classList.contains("skip")) return;
      var target = document.querySelector(link.getAttribute("href"));
      if (!target) return;
      event.preventDefault();
      if (lenis) {
        lenis.scrollTo(target, { offset: -72 });
      } else {
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      history.pushState(null, "", link.getAttribute("href"));
    });
  });

  window.gsap.utils.toArray("[data-reveal]").forEach(function (element) {
    window.gsap.to(element, {
      y: 0,
      opacity: 1,
      duration: 1.05,
      ease: "expo.out",
      scrollTrigger: {
        trigger: element,
        start: "top 88%",
        once: true
      }
    });
  });

  window.gsap.fromTo(".hero__rail-fill", { scaleX: 0 }, {
    scaleX: 1,
    duration: 1.5,
    delay: 1.25,
    ease: "expo.out"
  });

  var minute = document.querySelector("[data-minute]");
  if (minute) {
    var chapters = Array.prototype.slice.call(minute.querySelectorAll(".chapter"));
    var timeEl = minute.querySelector("[data-minute-time]");
    var quoteEl = minute.querySelector("[data-minute-quote]");
    var sourceEl = minute.querySelector("[data-minute-source]");
    var dot = minute.querySelector("[data-minute-dot]");
    var progress = minute.querySelector("[data-minute-progress]");
    var activeChapter = -1;

    var setChapter = function (index, animate) {
      if (index === activeChapter) return;
      activeChapter = index;
      var chapter = chapters[index];
      if (!chapter) return;

      if (timeEl) timeEl.textContent = chapter.getAttribute("data-time");
      if (quoteEl) quoteEl.textContent = chapter.getAttribute("data-quote");
      if (sourceEl) sourceEl.textContent = chapter.getAttribute("data-source");

      var position = chapters.length > 1 ? index / (chapters.length - 1) : 0;
      if (dot) dot.style.left = (8 + position * 84) + "%";
      if (progress) progress.style.transform = "scaleX(" + ((index + 1) / chapters.length) + ")";

      if (animate && quoteEl && timeEl) {
        window.gsap.fromTo([timeEl, quoteEl], { y: 10, opacity: 0 }, {
          y: 0,
          opacity: 1,
          duration: 0.45,
          ease: "power3.out",
          stagger: 0.05,
          overwrite: true
        });
      }
    };

    setChapter(0, false);

    chapters.forEach(function (chapter, index) {
      window.ScrollTrigger.create({
        trigger: chapter,
        start: "top 48%",
        end: "bottom 48%",
        onToggle: function (self) {
          if (self.isActive) setChapter(index, true);
        }
      });
    });
  }

  window.addEventListener("load", function () {
    window.ScrollTrigger.refresh();
  });
})();
