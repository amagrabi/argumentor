// Deep analysis: the paid second pass over an argument the user has already had
// evaluated. Never automatic — it costs ~16x a normal evaluation.
//
// Deliberately its own module rather than more of main.js. Static assets are
// served immutable for 7 days and are not fingerprinted, so an edit to main.js
// would not reach returning visitors for a week — and the button, which lives in
// the server-rendered template, would land immediately with nothing wired to it.
// A new filename has never been cached, so this ships together with the markup.
import { translations } from "./translations.js";

const t = () => translations?.evaluation?.deepAnalysis || {};

// The button is rendered only for Plus and Pro (see index.html): a visible
// button that 402s is worse than no button. The 402 branch below is therefore
// the safety net for a stale page, not the normal path.
const btn = document.getElementById("deepAnalysisBtn");
const output = document.getElementById("deepAnalysisResult");
const status = document.getElementById("deepAnalysisStatus");

// Which answer the currently rendered analysis belongs to. main.js clears the
// panel between submissions, but a stale cached main.js would not, so the id is
// re-checked here on every click.
let renderedFor = null;

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  // textContent throughout: the analysis is model output, and this panel is
  // rendered without a sanitiser.
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

function section(title, body) {
  const wrapper = el("div", "mb-6");
  wrapper.appendChild(el("h3", "text-lg font-bold mb-2", title));
  wrapper.appendChild(body);
  return wrapper;
}

function labelledParagraph(label, text) {
  const p = el("p", "text-sm text-gray-700 mt-1");
  p.appendChild(el("span", "font-semibold", `${label}: `));
  p.appendChild(document.createTextNode(text || ""));
  return p;
}

function render(analysis) {
  const s = t();
  output.replaceChildren();

  output.appendChild(el("h2", "text-2xl font-bold mb-1", s.title || "Deep analysis"));
  output.appendChild(
    el(
      "p",
      "text-sm text-gray-600 mb-6",
      s.subtitle ||
        "A structural critique of this argument: what it actually establishes, " +
          "what it assumes without arguing for, the strongest objections it never " +
          "met, and how to rebuild it."
    )
  );

  if (analysis.verdict) {
    output.appendChild(
      section(
        s.verdict || "What this argument actually establishes",
        el("p", "text-gray-800", analysis.verdict)
      )
    );
  }

  if (analysis.reconstruction?.length) {
    const list = el("ol", "list-decimal ml-5 space-y-3");
    for (const item of analysis.reconstruction) {
      const li = el("li");
      li.appendChild(el("p", "font-medium text-gray-900", item.step));
      li.appendChild(el("p", "text-sm text-gray-700 mt-1", item.assessment));
      list.appendChild(li);
    }
    output.appendChild(
      section(s.reconstruction || "How the argument works, step by step", list)
    );
  }

  if (analysis.unstated_assumptions?.length) {
    const list = el("ul", "space-y-3");
    for (const item of analysis.unstated_assumptions) {
      const li = el("li", "p-3 rounded-lg border border-gray-200 bg-gray-50");
      li.appendChild(el("p", "font-medium text-gray-900", item.assumption));
      li.appendChild(el("p", "text-sm text-gray-700 mt-1", item.why_it_matters));
      list.appendChild(li);
    }
    output.appendChild(
      section(s.assumptions || "What it assumes without arguing for", list)
    );
  }

  if (analysis.counterarguments?.length) {
    const list = el("ul", "space-y-4");
    for (const item of analysis.counterarguments) {
      const li = el("li", "p-4 rounded-lg border-2 border-amber-300 bg-amber-50");
      li.appendChild(el("p", "font-medium text-gray-900", item.objection));
      li.appendChild(labelledParagraph(s.whyItBites || "Why it bites", item.why_it_bites));
      li.appendChild(
        labelledParagraph(
          s.whatWouldAnswerIt || "What would answer it",
          item.what_would_answer_it
        )
      );
      list.appendChild(li);
    }
    output.appendChild(
      section(
        s.counterarguments || "The strongest objections it does not address",
        list
      )
    );
  }

  if (analysis.rebuild?.length) {
    const list = el("ol", "list-decimal ml-5 space-y-2");
    for (const step of analysis.rebuild) {
      list.appendChild(el("li", "text-gray-800", step));
    }
    output.appendChild(section(s.rebuild || "How to rebuild it", list));
  }

  output.classList.remove("hidden");
}

function showStatus(text) {
  if (!status) return;
  status.textContent = text;
  status.classList.remove("hidden");
}

function interpolate(template, values) {
  return Object.entries(values).reduce(
    (acc, [key, value]) => acc.replaceAll(`{${key}}`, value),
    template || ""
  );
}

// Exported so main.js can clear the panel when a new answer is submitted. Guard
// the call site with a typeof check: a cached main.js predating this module
// would not import it, and this module must keep working on its own.
export function resetDeepAnalysis() {
  renderedFor = null;
  if (output) {
    output.replaceChildren();
    output.classList.add("hidden");
  }
  if (status) status.classList.add("hidden");
  if (btn) btn.disabled = false;
}
window.resetDeepAnalysis = resetDeepAnalysis;

if (btn && output) {
  btn.addEventListener("click", async () => {
    const answerId = sessionStorage.getItem("lastAnswerId");
    if (!answerId) return;

    // A stale panel from a previous answer must never be mistaken for this one.
    if (renderedFor && renderedFor !== answerId) resetDeepAnalysis();
    if (renderedFor === answerId) {
      output.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const s = t();
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = s.running || "Analysing your argument…";
    showStatus(s.runningHint || "");

    try {
      const res = await fetch("/deep_analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer_id: answerId }),
      });
      const data = await res.json().catch(() => ({}));

      if (res.status === 402) {
        // Only reachable from a page rendered before the tier changed.
        showStatus(data.error || "Deep analysis is available on Plus and Pro.");
        return;
      }
      if (res.status === 429) {
        showStatus(
          data.error ||
            interpolate(s.limitReached, { limit: btn.dataset.limit || "" }) ||
            "You have used all of this month's deep analyses."
        );
        return;
      }
      if (!res.ok || !data.analysis) {
        showStatus(s.failed || "Deep analysis failed. Please try again.");
        return;
      }

      render(data.analysis);
      renderedFor = answerId;

      if (data.cached) {
        showStatus(s.cached || "");
      } else if (typeof data.remaining === "number" && btn.dataset.limit) {
        showStatus(
          interpolate(s.remaining || "{remaining} of {limit} left this month.", {
            remaining: data.remaining,
            limit: btn.dataset.limit,
          })
        );
      } else if (status) {
        status.classList.add("hidden");
      }

      // preventScroll is not needed here — nothing takes focus — but the panel
      // is still laying out, so scroll after the browser has applied it.
      requestAnimationFrame(() =>
        output.scrollIntoView({ behavior: "smooth", block: "start" })
      );
    } catch (err) {
      console.error("Deep analysis request failed:", err);
      showStatus(s.failed || "Deep analysis failed. Please try again.");
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  });
}
