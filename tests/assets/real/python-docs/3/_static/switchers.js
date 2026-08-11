"use strict";

// File URIs must begin with either one or three forward slashes
const _is_file_uri = (uri) => uri.startsWith("file:/");

const _IS_LOCAL = _is_file_uri(window.location.href);
const _CURRENT_RELEASE = DOCUMENTATION_OPTIONS.VERSION || "";
const _CURRENT_VERSION = _CURRENT_RELEASE.split(".", 2).join(".");
const _CURRENT_LANGUAGE = (() => {
  const _LANGUAGE = DOCUMENTATION_OPTIONS.LANGUAGE?.toLowerCase() || "en";
  // Python 2.7 and 3.5--3.10 use ``LANGUAGE: 'None'`` for English
  // in ``documentation_options.js``.
  if (_LANGUAGE === "none") return "en";
  return _LANGUAGE;
})();
const _CURRENT_PREFIX = (() => {
  if (_IS_LOCAL) return null;
  // Sphinx 7.2+ defines the content root data attribute in the HTML element.
  const _CONTENT_ROOT = document.documentElement.dataset.content_root;
  if (_CONTENT_ROOT !== undefined) {
    return new URL(_CONTENT_ROOT, window.location).pathname;
  }
  // Fallback for older versions of Sphinx (used in Python 3.10 and older).
  const _NUM_PREFIX_PARTS = _CURRENT_LANGUAGE === "en" ? 2 : 3;
  return window.location.pathname.split("/", _NUM_PREFIX_PARTS).join("/") + "/";
})();

const _ALL_VERSIONS = new Map([["3.16", "dev (3.16)"], ["3.15", "pre (3.15)"], ["3.14", "3.14"], ["3.13", "3.13"], ["3.12", "3.12"], ["3.11", "3.11"], ["3.10", "3.10"], ["3.9", "3.9"], ["3.8", "3.8"], ["3.7", "3.7"], ["3.6", "3.6"], ["3.5", "3.5"], ["3.4", "3.4"], ["3.3", "3.3"], ["3.2", "3.2"], ["3.1", "3.1"], ["3.0", "3.0"], ["2.7", "2.7"], ["2.6", "2.6"]]);
const _ALL_LANGUAGES = new Map([["el", "Greek | \u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac"], ["en", "English"], ["es", "Spanish | espa\u00f1ol"], ["fr", "French | fran\u00e7ais"], ["it", "Italian | italiano"], ["ja", "Japanese | \u65e5\u672c\u8a9e"], ["ko", "Korean | \ud55c\uad6d\uc5b4"], ["pl", "Polish | polski"], ["pt-br", "Brazilian Portuguese | Portugu\u00eas brasileiro"], ["ro", "Romanian | Rom\u00e2ne\u0219te"], ["tr", "Turkish | T\u00fcrk\u00e7e"], ["zh-cn", "Simplified Chinese | \u7b80\u4f53\u4e2d\u6587"], ["zh-tw", "Traditional Chinese | \u7e41\u9ad4\u4e2d\u6587"]]);

/**
 * Required for Python 3.7 and earlier.
 * @returns {void}
 * @private
 */
const _create_placeholders_if_missing = () => {
  if (document.querySelectorAll(".version_switcher_placeholder").length) return;

  const items = document.querySelectorAll("body>div.related>ul>li:not(.right)");
  for (const item of items) {
    if (item.innerText.toLowerCase().includes("documentation")) {
      const container = document.createElement("li");
      container.className = "switchers";
      container.style.display = "inline-flex";
      for (const placeholder_name of ["language", "version"]) {
        const placeholder = document.createElement("div");
        placeholder.className = `${placeholder_name}_switcher_placeholder`;
        placeholder.style.marginRight = "5px";
        placeholder.style.paddingLeft = "5px";
        container.appendChild(placeholder);
      }
      item.parentElement.insertBefore(container, item);
      return;
    }
  }
};

/**
 * @param {Map<string, string>} versions
 * @returns {HTMLSelectElement}
 * @private
 */
const _create_version_select = (versions) => {
  const select = document.createElement("select");
  select.className = "version-select";
  select.setAttribute("aria-label", "Python version");
  if (_IS_LOCAL) {
    select.disabled = true;
    select.title = "Version switching is disabled in local builds";
  }

  for (const [version, title] of versions) {
    const option = document.createElement("option");
    option.value = version;
    if (version === _CURRENT_VERSION) {
      option.text = _CURRENT_RELEASE;
      option.selected = true;
    } else {
      option.text = title;
    }
    select.add(option);
  }

  return select;
};

/**
 * @param {Map<string, string>} languages
 * @returns {HTMLSelectElement}
 * @private
 */
const _create_language_select = (languages) => {
  if (!languages.has(_CURRENT_LANGUAGE)) {
    // In case we are browsing a language that is not yet in languages.
    languages.set(_CURRENT_LANGUAGE, _CURRENT_LANGUAGE);
  }

  const select = document.createElement("select");
  select.className = "language-select";
  select.setAttribute("aria-label", "Language");
  if (_IS_LOCAL) {
    select.disabled = true;
    select.title = "Language switching is disabled in local builds";
  }

  for (const [language, title] of languages) {
    const option = document.createElement("option");
    option.value = language;
    option.text = title;
    if (language === _CURRENT_LANGUAGE) option.selected = true;
    select.add(option);
  }

  return select;
};

/**
 * Change the current page to the first existing URL in the list.
 * @param {Array<string>} urls
 * @private
 */
const _navigate_to_first_existing = async (urls) => {
  // Navigate to the first existing URL in urls.
  for (const url of urls) {
    try {
      const response = await fetch(url, { method: "HEAD" });
      if (response.ok) {
        window.location.href = url;
        return url;
      }
    } catch (err) {
      console.error(`Error when fetching '${url}': ${err}`);
    }
  }

  // if all else fails, redirect to the d.p.o root
  window.location.href = "/";
  return "/";
};

/**
 * Navigate to the selected version.
 * @param {Event} event
 * @returns {void}
 * @private
 */
const _on_version_switch = async (event) => {
  if (_IS_LOCAL) return;

  const selected_version = event.target.value;
  // English has no language prefix.
  const new_prefix_en = `/${selected_version}/`;
  const new_prefix =
    _CURRENT_LANGUAGE === "en"
      ? new_prefix_en
      : `/${_CURRENT_LANGUAGE}/${selected_version}/`;
  if (_CURRENT_PREFIX !== new_prefix) {
    // Try the following pages in order:
    // 1. The current page in the current language with the new version
    // 2. The current page in English with the new version
    // 3. The documentation home in the current language with the new version
    // 4. The documentation home in English with the new version
    await _navigate_to_first_existing([
      window.location.href.replace(_CURRENT_PREFIX, new_prefix),
      window.location.href.replace(_CURRENT_PREFIX, new_prefix_en),
      new_prefix,
      new_prefix_en,
    ]);
  }
};

/**
 * Navigate to the selected language.
 * @param {Event} event
 * @returns {void}
 * @private
 */
const _on_language_switch = async (event) => {
  if (_IS_LOCAL) return;

  const selected_language = event.target.value;
  // English has no language prefix.
  const new_prefix =
    selected_language === "en"
      ? `/${_CURRENT_VERSION}/`
      : `/${selected_language}/${_CURRENT_VERSION}/`;
  if (_CURRENT_PREFIX !== new_prefix) {
    // Try the following pages in order:
    // 1. The current page in the new language with the current version
    // 2. The documentation home in the new language with the current version
    await _navigate_to_first_existing([
      window.location.href.replace(_CURRENT_PREFIX, new_prefix),
      new_prefix,
    ]);
  }
};

/**
 * Set up the version and language switchers.
 * @returns {void}
 * @private
 */
const _initialise_switchers = () => {
  const versions = _ALL_VERSIONS;
  const languages = _ALL_LANGUAGES;

  _create_placeholders_if_missing();

  document
    .querySelectorAll(".version_switcher_placeholder")
    .forEach((placeholder) => {
      const s = _create_version_select(versions);
      s.addEventListener("change", _on_version_switch);
      placeholder.append(s);
    });

  document
    .querySelectorAll(".language_switcher_placeholder")
    .forEach((placeholder) => {
      const s = _create_language_select(languages);
      s.addEventListener("change", _on_language_switch);
      placeholder.append(s);
    });
};

if (document.readyState !== "loading") {
  _initialise_switchers();
} else {
  document.addEventListener("DOMContentLoaded", _initialise_switchers);
}
