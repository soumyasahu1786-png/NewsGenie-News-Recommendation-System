(function () {
  const THEME_KEY = "newsgenie-theme";
  const CATEGORY_KEYS = ["tech", "finance", "sports", "health", "entertainment", "general"];

  function setTheme(mode) {
    document.body.classList.toggle("dark", mode === "dark");
    const btn = document.getElementById("themeToggle");
    if (btn) btn.textContent = mode === "dark" ? "☀️" : "🌙";
    localStorage.setItem(THEME_KEY, mode);
  }

  function initTheme() {
    setTheme(localStorage.getItem(THEME_KEY) || "light");
    const btn = document.getElementById("themeToggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      setTheme(document.body.classList.contains("dark") ? "light" : "dark");
    });
  }

  function getHighestCategory(values) {
    let top = "general";
    let score = -1;
    CATEGORY_KEYS.forEach(function (key) {
      const next = Number(values[key] || 0);
      if (next > score) {
        score = next;
        top = key;
      }
    });
    return top;
  }

  function initPreferencesPage() {
    const form = document.getElementById("preferencesForm");
    if (!form) return;

    const sliders = Array.from(document.querySelectorAll(".interest-slider"));
    const voiceBtn = document.getElementById("voiceBtn");
    const voiceStatus = document.getElementById("voiceStatus");

    function getSliderValues() {
      const out = {};
      sliders.forEach(function (slider) {
        out[slider.dataset.category] = Number(slider.value);
      });
      return out;
    }

    function refreshSliderLabels() {
      sliders.forEach(function (slider) {
        const valueNode = document.querySelector('[data-value-for="' + slider.dataset.category + '"]');
        if (valueNode) valueNode.textContent = Number(slider.value).toFixed(1);
      });
    }

    sliders.forEach(function (slider) {
      slider.addEventListener("input", refreshSliderLabels);
    });
    refreshSliderLabels();

    form.addEventListener("submit", function () {
      const values = getSliderValues();
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "category";
      hidden.value = getHighestCategory(values);
      form.appendChild(hidden);
    });

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!voiceBtn || !voiceStatus) return;
    if (!SpeechRecognition) {
      voiceBtn.disabled = true;
      voiceStatus.textContent = "Speech recognition not supported in this browser.";
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    const aliases = {
      tech: ["tech", "technology", "tek"],
      finance: ["finance", "financial", "business", "paisa", "arthvyavastha"],
      sports: ["sports", "sport", "cricket", "football", "khel"],
      health: ["health", "medical", "fitness", "sehat", "swasthya"],
      entertainment: ["entertainment", "movie", "movies", "bollywood", "cinema", "manoranjan"],
      general: ["general", "news", "samachar", "khabar"],
    };

    function markDetectedCategories(text) {
      const hits = [];
      CATEGORY_KEYS.forEach(function (category) {
        const words = aliases[category] || [];
        const found = words.some(function (w) {
          return text.includes(w);
        });
        if (found) {
          const slider = document.querySelector('.interest-slider[data-category="' + category + '"]');
          if (slider) slider.value = "1";
          hits.push(category);
        }
      });
      refreshSliderLabels();
      return hits;
    }

    voiceBtn.addEventListener("click", function () {
      voiceStatus.textContent = "Listening... बोलिए / Speak now";
      recognition.start();
    });

    recognition.onresult = function (event) {
      const transcript = ((event.results[0] || [])[0] || {}).transcript || "";
      const lower = transcript.toLowerCase();
      const hits = markDetectedCategories(lower);
      voiceStatus.textContent = 'Heard: "' + transcript + '"' + (hits.length ? " -> Updated: " + hits.join(", ") : " -> No category matched");
    };

    recognition.onerror = function () {
      voiceStatus.textContent = "Voice capture failed. Please try again.";
    };
  }

  function createArticleCard(article) {
    const image = article.image
      ? '<img class="news-image" src="' + article.image + '" alt="News image" loading="lazy">'
      : '<img class="news-image" src="https://images.unsplash.com/photo-1504711331083-9c895941bf81?auto=format&fit=crop&w=1200&q=60" alt="News image" loading="lazy">';

    return (
      '<article class="news-card fade-up">' +
      image +
      '<div class="news-content">' +
      '<div class="meta"><span>' + (article.source || "Unknown") + "</span><span class=\"badge\">" + (article.category || "General") + "</span></div>" +
      "<h3>" + (article.title || "Untitled") + "</h3>" +
      "<p>" + (article.description || "No description available.") + "</p>" +
      '<a class="btn-ghost" href="' + (article.url || "#") + '" target="_blank" rel="noopener noreferrer">Read More</a>' +
      "</div></article>"
    );
  }

  async function initFeedPage() {
    const body = document.body;
    if (body.dataset.page !== "feed") return;

    const categories = (body.dataset.categories || "general")
      .split(",")
      .map(function (v) { return v.trim().toLowerCase(); })
      .filter(Boolean);
    const loaderWrap = document.getElementById("loaderWrap");
    const grid = document.getElementById("feedGrid");
    const emptyState = document.getElementById("emptyState");

    try {
      const results = await Promise.all(
        categories.map(function (cat) {
          return fetch("/get_feed?category=" + encodeURIComponent(cat)).then(function (res) { return res.json(); });
        })
      );

      const seen = new Set();
      const articles = [];
      results.forEach(function (result) {
        (result.articles || []).forEach(function (article) {
          const key = article.url || article.title;
          if (!seen.has(key)) {
            seen.add(key);
            articles.push(article);
          }
        });
      });

      loaderWrap.classList.add("hidden");
      if (!articles.length) {
        emptyState.classList.remove("hidden");
        emptyState.textContent = "No news available for selected interests right now.";
        return;
      }
      grid.innerHTML = articles.map(createArticleCard).join("");
    } catch (err) {
      loaderWrap.classList.add("hidden");
      emptyState.classList.remove("hidden");
      emptyState.textContent = "Network error while loading news.";
      console.error(err);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initPreferencesPage();
    initFeedPage();
  });
  window.togglePassword = function () {
  const passwordField = document.getElementById("password");

  if (passwordField.type === "password") {
    passwordField.type = "text";
  } else {
    passwordField.type = "password";
  }
};
})();
