(function () {
  "use strict";

  const initialPayload = window.__PF_INITIAL_PAYLOAD__ || null;
  const appConfig = window.__PF_APP_CONFIG__ || {};

  const elements = {
    intakeView: document.getElementById("intake-view"),
    loadingView: document.getElementById("loading-view"),
    errorView: document.getElementById("error-view"),
    workspaceView: document.getElementById("workspace-view"),
    topbarStatus: document.getElementById("topbar-status"),
    uploadInput: document.getElementById("upload-input"),
    chooseFile: document.getElementById("choose-file"),
    analyzeButton: document.getElementById("analyze-button"),
    dropzone: document.getElementById("dropzone"),
    uploadSummary: document.getElementById("upload-summary"),
    corpusLabel: document.getElementById("corpus-label"),
    loadingMessage: document.getElementById("loading-message"),
    loadingProgress: document.getElementById("loading-progress"),
    loadingSteps: document.getElementById("loading-steps"),
    errorMessage: document.getElementById("error-message"),
    errorReset: document.getElementById("error-reset"),
    documentTitle: document.getElementById("document-title"),
    documentSubtitle: document.getElementById("document-subtitle"),
    summaryGrid: document.getElementById("summary-grid"),
    filterSection: document.getElementById("filter-section"),
    filterPlagiarism: document.getElementById("filter-plagiarism"),
    filterPlagiarismValue: document.getElementById("filter-plagiarism-value"),
    filterAi: document.getElementById("filter-ai"),
    filterAiValue: document.getElementById("filter-ai-value"),
    filterFlagged: document.getElementById("filter-flagged"),
    filterMatches: document.getElementById("filter-matches"),
    filterTriggers: document.getElementById("filter-triggers"),
    filterSearch: document.getElementById("filter-search"),
    spanNavigator: document.getElementById("span-navigator"),
    outlineNav: document.getElementById("outline-nav"),
    legendCaveat: document.getElementById("legend-caveat"),
    viewMode: document.getElementById("view-mode"),
    textMode: document.getElementById("text-mode"),
    densityMode: document.getElementById("density-mode"),
    sortMode: document.getElementById("sort-mode"),
    resultCount: document.getElementById("result-count"),
    documentList: document.getElementById("document-list"),
    inspectorTitle: document.getElementById("inspector-title"),
    inspectorLocation: document.getElementById("inspector-location"),
    inspectorEmpty: document.getElementById("inspector-empty"),
    inspectorContent: document.getElementById("inspector-content"),
    exportActions: document.getElementById("export-actions"),
    scorecards: document.getElementById("scorecards"),
    inspectorSummary: document.getElementById("inspector-summary"),
    flagReason: document.getElementById("flag-reason"),
    plagiarismFeatures: document.getElementById("plagiarism-features"),
    aiFeatures: document.getElementById("ai-features"),
    matchList: document.getElementById("match-list"),
    triggeredPhrases: document.getElementById("triggered-phrases"),
    triggeredCategories: document.getElementById("triggered-categories"),
    sourceContext: document.getElementById("source-context"),
    scoringNote: document.getElementById("scoring-note"),
  };

  const state = {
    mode: appConfig.mode || "report",
    uploadFile: null,
    currentJobId: null,
    payload: initialPayload,
    selectedSentenceId: initialPayload && initialPayload.rows[0] ? initialPayload.rows[0].sentence_id : null,
    filters: {
      section: "all",
      plagiarism: 0,
      ai: 0,
      flaggedOnly: false,
      matchesOnly: false,
      triggersOnly: false,
      search: "",
    },
    viewMode: "sentence",
    textMode: "clean",
    density: "comfortable",
    sortMode: "document",
  };

  const pollingTimers = new Set();

  function init() {
    bindStaticEvents();
    if (state.payload) {
      setView("workspace");
      renderWorkspace(true);
    } else if (state.mode === "app") {
      setView("intake");
      elements.corpusLabel.textContent = appConfig.corpus_label || "Corpus not configured";
    } else {
      setView("error");
      elements.errorMessage.textContent = "No review payload was available for this report.";
    }
  }

  function bindStaticEvents() {
    if (elements.chooseFile) {
      elements.chooseFile.addEventListener("click", () => elements.uploadInput.click());
    }
    if (elements.uploadInput) {
      elements.uploadInput.addEventListener("change", (event) => {
        const file = event.target.files && event.target.files[0];
        if (file) {
          setUploadFile(file);
        }
      });
    }
    if (elements.dropzone) {
      ["dragenter", "dragover"].forEach((eventName) => {
        elements.dropzone.addEventListener(eventName, (event) => {
          event.preventDefault();
          elements.dropzone.classList.add("is-dragging");
        });
      });
      ["dragleave", "drop"].forEach((eventName) => {
        elements.dropzone.addEventListener(eventName, (event) => {
          event.preventDefault();
          elements.dropzone.classList.remove("is-dragging");
        });
      });
      elements.dropzone.addEventListener("drop", (event) => {
        const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
        if (file) {
          setUploadFile(file);
        }
      });
      elements.dropzone.addEventListener("click", () => elements.uploadInput.click());
      elements.dropzone.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          elements.uploadInput.click();
        }
      });
    }
    if (elements.analyzeButton) {
      elements.analyzeButton.addEventListener("click", startAnalysis);
    }
    if (elements.errorReset) {
      elements.errorReset.addEventListener("click", () => {
        setView("intake");
        elements.errorMessage.textContent = "";
      });
    }

    [
      elements.filterSection,
      elements.filterPlagiarism,
      elements.filterAi,
      elements.filterFlagged,
      elements.filterMatches,
      elements.filterTriggers,
      elements.filterSearch,
      elements.viewMode,
      elements.textMode,
      elements.densityMode,
      elements.sortMode,
    ].forEach((element) => {
      if (!element) return;
      element.addEventListener("input", handleControlChange);
      element.addEventListener("change", handleControlChange);
    });

    document.addEventListener("keydown", handleKeydown);
  }

  function setUploadFile(file) {
    state.uploadFile = file;
    elements.uploadSummary.innerHTML = `
      <div><strong>${escapeHtml(file.name)}</strong></div>
      <div class="pf-muted">Size: ${formatFileSize(file.size)} · Type: ${escapeHtml(file.type || "unknown")}</div>
      <div class="pf-muted">Supported formats: .tex, .zip, .tar, .tar.gz, .tgz</div>
    `;
    elements.analyzeButton.disabled = false;
  }

  function setView(view) {
    const visibility = {
      intake: view === "intake",
      loading: view === "loading",
      error: view === "error",
      workspace: view === "workspace",
    };
    elements.intakeView.hidden = !visibility.intake;
    elements.loadingView.hidden = !visibility.loading;
    elements.errorView.hidden = !visibility.error;
    elements.workspaceView.hidden = !visibility.workspace;
  }

  async function startAnalysis() {
    if (!state.uploadFile) return;
    setView("loading");
    updateLoadingState(0.12, "Uploading manuscript", 0);
    try {
      const form = new FormData();
      form.append("manuscript", state.uploadFile, state.uploadFile.name);
      const response = await fetch(appConfig.create_job_endpoint || "/api/jobs", {
        method: "POST",
        body: form,
      });
      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}.`);
      }
      const payload = await response.json();
      state.currentJobId = payload.job_id;
      pollJob(payload.job_id);
    } catch (error) {
      showError(error.message || "Unable to start analysis.");
    }
  }

  function pollJob(jobId) {
    const tick = async () => {
      try {
        const response = await fetch((appConfig.job_status_prefix || "/api/jobs/") + encodeURIComponent(jobId), {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Status polling failed with ${response.status}.`);
        }
        const payload = await response.json();
        const stageIndex = stageIndexFor(payload.stage);
        updateLoadingState(payload.progress || estimatedProgress(stageIndex), payload.message || "Analyzing document", stageIndex);
        if (payload.status === "completed" && payload.review_payload) {
          state.payload = payload.review_payload;
          state.selectedSentenceId = state.payload.rows[0] ? state.payload.rows[0].sentence_id : null;
          setView("workspace");
          renderWorkspace(true);
          return;
        }
        if (payload.status === "failed") {
          showError(payload.error || "Analysis failed.");
          return;
        }
        const timer = window.setTimeout(tick, 850);
        pollingTimers.add(timer);
      } catch (error) {
        showError(error.message || "Unable to poll analysis status.");
      }
    };
    tick();
  }

  function stageIndexFor(stage) {
    const stages = ["preparing", "resolving", "analyzing", "finalizing"];
    const index = stages.indexOf(stage);
    return index >= 0 ? index : 0;
  }

  function estimatedProgress(stageIndex) {
    return [0.16, 0.35, 0.72, 0.95][stageIndex] || 0.12;
  }

  function updateLoadingState(progress, message, activeIndex) {
    elements.loadingMessage.textContent = message;
    elements.loadingProgress.style.width = `${Math.round(progress * 100)}%`;
    Array.from(elements.loadingSteps.children).forEach((item, index) => {
      item.classList.toggle("is-active", index === activeIndex);
    });
  }

  function showError(message) {
    clearTimers();
    setView("error");
    elements.errorMessage.textContent = message;
  }

  function clearTimers() {
    pollingTimers.forEach((timer) => window.clearTimeout(timer));
    pollingTimers.clear();
  }

  function handleControlChange() {
    if (!state.payload) return;
    state.filters.section = elements.filterSection.value;
    state.filters.plagiarism = Number(elements.filterPlagiarism.value);
    state.filters.ai = Number(elements.filterAi.value);
    state.filters.flaggedOnly = elements.filterFlagged.checked;
    state.filters.matchesOnly = elements.filterMatches.checked;
    state.filters.triggersOnly = elements.filterTriggers.checked;
    state.filters.search = elements.filterSearch.value.trim().toLowerCase();
    state.viewMode = elements.viewMode.value;
    state.textMode = elements.textMode.value;
    state.density = elements.densityMode.value;
    state.sortMode = elements.sortMode.value;
    renderWorkspace(false);
  }

  function renderWorkspace(firstRender) {
    const payload = state.payload;
    if (!payload) return;

    elements.topbarStatus.textContent = "Review workspace ready";
    elements.documentTitle.textContent = payload.document.title;
    elements.documentSubtitle.textContent = `${payload.document.input_name} · ${payload.document.sentence_count} sentences · ${payload.document.paragraph_count} paragraphs`;
    elements.legendCaveat.textContent = payload.legend.caveat;

    if (firstRender) {
      populateSectionFilter(payload.filters.sections);
      elements.filterPlagiarism.value = String(payload.filters.default_plagiarism_threshold);
      elements.filterAi.value = String(payload.filters.default_ai_threshold);
      state.filters.plagiarism = Number(elements.filterPlagiarism.value);
      state.filters.ai = Number(elements.filterAi.value);
    }

    elements.filterPlagiarismValue.textContent = Number(elements.filterPlagiarism.value).toFixed(2);
    elements.filterAiValue.textContent = Number(elements.filterAi.value).toFixed(2);
    renderSummary(payload);
    renderOutline(payload);
    renderSpans(payload);
    renderDocument(payload);
    renderInspector(payload);
    renderExports(payload);
  }

  function populateSectionFilter(sections) {
    elements.filterSection.innerHTML = `<option value="all">All sections</option>${sections
      .map((section) => `<option value="${escapeHtml(section)}">${escapeHtml(section)}</option>`)
      .join("")}`;
  }

  function renderSummary(payload) {
    const metrics = payload.metrics;
    const cards = [
      ["Flagged sentences", metrics.flagged_sentence_count],
      ["External matches", metrics.external_match_count],
      ["Style triggers", metrics.triggered_sentence_count],
      ["Suspicious spans", metrics.suspicious_span_count],
    ];
    elements.summaryGrid.innerHTML = cards
      .map(
        ([label, value]) => `
          <div class="pf-summary-card">
            <span class="pf-muted">${escapeHtml(label)}</span>
            <strong>${escapeHtml(String(value))}</strong>
          </div>
        `
      )
      .join("");
  }

  function renderOutline(payload) {
    elements.outlineNav.innerHTML = payload.outline
      .map((section) => {
        const subsectionMarkup = section.subsections
          .map(
            (subsection) => `
              <button type="button" class="pf-nav-item" data-outline-target="${escapeHtml(subsection.paragraph_ids[0] || "")}">
                <strong>${escapeHtml(subsection.label)}</strong>
                <span class="pf-nav-item__meta">${subsection.sentence_count} sentences · ${subsection.flagged_count} flagged</span>
              </button>
            `
          )
          .join("");
        return `
          <button type="button" class="pf-nav-item" data-outline-target="${escapeHtml(section.paragraph_ids[0] || "")}">
            <strong>${escapeHtml(section.label)}</strong>
            <span class="pf-nav-item__meta">${section.sentence_count} sentences · ${section.flagged_count} flagged · ${escapeHtml(
              lineLabel(section.line_start, section.line_end)
            )}</span>
          </button>
          ${subsectionMarkup}
        `;
      })
      .join("");
    elements.outlineNav.querySelectorAll("[data-outline-target]").forEach((button) => {
      button.addEventListener("click", () => jumpToParagraph(button.getAttribute("data-outline-target")));
    });
  }

  function renderSpans(payload) {
    if (!payload.suspicious_spans.length) {
      elements.spanNavigator.innerHTML = `<div class="pf-empty">No suspicious spans met the current review baseline.</div>`;
      return;
    }
    elements.spanNavigator.innerHTML = payload.suspicious_spans
      .map(
        (span) => `
          <button type="button" class="pf-nav-item" data-span-id="${escapeHtml(span.span_id)}">
            <strong>${escapeHtml(span.label)}</strong>
            <span class="pf-nav-item__meta">${escapeHtml(span.line_label)} · max risk ${span.max_combined_risk.toFixed(
              2
            )}</span>
          </button>
        `
      )
      .join("");
    elements.spanNavigator.querySelectorAll("[data-span-id]").forEach((button) => {
      button.addEventListener("click", () => jumpToSpan(button.getAttribute("data-span-id")));
    });
  }

  function renderDocument(payload) {
    const visibleRows = getVisibleRows(payload);
    ensureSelectedVisible(visibleRows, payload.rows);
    elements.resultCount.textContent = `${visibleRows.length} of ${payload.rows.length} sentences shown`;
    elements.documentList.dataset.density = state.density;

    if (!visibleRows.length) {
      elements.documentList.innerHTML = `<div class="pf-empty">No sentences match the current filters. Lower a threshold or widen the search to continue review.</div>`;
      return;
    }

    if (state.viewMode === "paragraph") {
      const paragraphs = getVisibleParagraphs(payload, visibleRows);
      elements.documentList.innerHTML = paragraphs.map((paragraph) => paragraphCard(paragraph)).join("");
      bindParagraphInteractions();
      return;
    }

    const groups = groupRowsBySection(visibleRows);
    elements.documentList.innerHTML = groups
      .map(
        (group) => `
          <section class="pf-group">
            <h3>${escapeHtml(group.section)}</h3>
            ${group.rows.map((row) => sentenceRow(row)).join("")}
          </section>
        `
      )
      .join("");
    bindSentenceInteractions();
  }

  function groupRowsBySection(rows) {
    const groups = [];
    rows.forEach((row) => {
      const last = groups[groups.length - 1];
      if (!last || last.section !== row.section) {
        groups.push({ section: row.section || "Untitled", rows: [row] });
      } else {
        last.rows.push(row);
      }
    });
    return groups;
  }

  function sentenceRow(row) {
    const text = state.textMode === "raw" ? row.raw_tex_fragment : row.clean_text;
    const activeClass = row.sentence_id === state.selectedSentenceId ? " is-active" : "";
    const triggerPills = row.triggered_phrases.length
      ? row.triggered_phrases.slice(0, 3).map((phrase) => `<span class="pf-pill">${escapeHtml(phrase)}</span>`).join("")
      : `<span class="pf-pill">No style trigger</span>`;
    return `
      <article class="pf-row${activeClass}" data-sentence-id="${escapeHtml(row.sentence_id)}" data-paragraph-id="${escapeHtml(
      row.paragraph_id
    )}" tabindex="0">
        <div class="pf-row__body">
          <div class="pf-row__meta">
            <div class="pf-row__identity">
              <strong>${escapeHtml(row.sentence_id)}</strong>
              <span>${escapeHtml(row.location_label)}</span>
            </div>
            <div class="pf-badges">
              <span class="pf-badge pf-badge--plagiarism">${escapeHtml(appConfig.plagiarism_label || "Overlap")} ${row.plagiarism_risk_score.toFixed(
      2
    )}</span>
              <span class="pf-badge pf-badge--ai">${escapeHtml(appConfig.ai_label || "AI-style")} ${row.ai_rhetoric_risk_score.toFixed(
      2
    )}</span>
              ${row.is_flagged ? `<span class="pf-badge pf-badge--flag">Review required</span>` : ""}
            </div>
          </div>
          <div class="pf-row__text">${escapeHtml(text)}</div>
          <div class="pf-row__summary">${escapeHtml(row.summary)}</div>
          <div class="pf-row__footer">
            <div class="pf-pill-list">${triggerPills}</div>
            <div class="pf-muted">${escapeHtml(row.source_context_label)}</div>
          </div>
        </div>
      </article>
    `;
  }

  function paragraphCard(paragraph) {
    const activeClass = paragraph.sentence_ids.includes(state.selectedSentenceId) ? " is-active" : "";
    const text = state.textMode === "raw" ? paragraph.raw_tex_context : paragraph.display_text;
    const sentenceMarkup = paragraph.rows
      .map((row) => {
        const activeSentence = row.sentence_id === state.selectedSentenceId ? " is-active" : "";
        return `
          <div class="pf-paragraph__sentence${activeSentence}" data-sentence-id="${escapeHtml(row.sentence_id)}">
            <strong>${escapeHtml(row.sentence_id)}</strong>
            <div class="pf-muted">${escapeHtml(state.textMode === "raw" ? row.raw_tex_fragment : row.clean_text)}</div>
          </div>
        `;
      })
      .join("");
    return `
      <article class="pf-paragraph${activeClass}" data-paragraph-id="${escapeHtml(paragraph.paragraph_id)}">
        <div class="pf-paragraph__body">
          <div class="pf-paragraph__meta">
            <div class="pf-paragraph__identity">
              <strong>${escapeHtml(paragraph.paragraph_id)}</strong>
              <span>${escapeHtml(paragraph.location_label)}</span>
            </div>
            <div class="pf-badges">
              <span class="pf-badge pf-badge--plagiarism">Overlap ${paragraph.plagiarism_risk_score.toFixed(2)}</span>
              <span class="pf-badge pf-badge--ai">AI-style ${paragraph.ai_rhetoric_risk_score.toFixed(2)}</span>
              ${paragraph.is_flagged ? `<span class="pf-badge pf-badge--flag">Review required</span>` : ""}
            </div>
          </div>
          <div class="pf-paragraph__text">${escapeHtml(text)}</div>
          <div class="pf-paragraph__summary">${escapeHtml(
            paragraph.has_external_match || paragraph.has_ai_trigger
              ? "Evidence is present within this paragraph. Select a sentence for detailed inspection."
              : "Lower-signal paragraph. Select a sentence if context review is needed."
          )}</div>
          <div class="pf-paragraph__sentences">${sentenceMarkup}</div>
        </div>
      </article>
    `;
  }

  function bindSentenceInteractions() {
    elements.documentList.querySelectorAll("[data-sentence-id]").forEach((node) => {
      node.addEventListener("click", () => selectSentence(node.getAttribute("data-sentence-id"), true));
    });
  }

  function bindParagraphInteractions() {
    elements.documentList.querySelectorAll(".pf-paragraph__sentence[data-sentence-id]").forEach((node) => {
      node.addEventListener("click", (event) => {
        event.stopPropagation();
        selectSentence(node.getAttribute("data-sentence-id"), true);
      });
    });
    elements.documentList.querySelectorAll(".pf-paragraph[data-paragraph-id]").forEach((paragraphNode) => {
      paragraphNode.addEventListener("click", () => {
        const firstSentence = paragraphNode.querySelector("[data-sentence-id]");
        if (firstSentence) {
          selectSentence(firstSentence.getAttribute("data-sentence-id"), true);
        }
      });
    });
  }

  function renderInspector(payload) {
    const row = findRowById(payload.rows, state.selectedSentenceId);
    if (!row) {
      elements.inspectorEmpty.hidden = false;
      elements.inspectorContent.hidden = true;
      elements.inspectorTitle.textContent = "Select a sentence";
      elements.inspectorLocation.textContent = "Sentence-level evidence appears here.";
      return;
    }

    elements.inspectorEmpty.hidden = true;
    elements.inspectorContent.hidden = false;
    elements.inspectorTitle.textContent = row.sentence_id;
    elements.inspectorLocation.textContent = `${row.location_label} · ${shortName(row.source_file)}`;
    elements.topbarStatus.textContent = `${row.sentence_id} selected`;
    elements.scorecards.innerHTML = `
      <div class="pf-scorecard pf-scorecard--plagiarism">
        <span class="pf-muted">Estimated overlap risk</span>
        <strong>${row.plagiarism_risk_score.toFixed(2)}</strong>
      </div>
      <div class="pf-scorecard pf-scorecard--ai">
        <span class="pf-muted">Estimated AI-style risk</span>
        <strong>${row.ai_rhetoric_risk_score.toFixed(2)}</strong>
      </div>
    `;
    elements.inspectorSummary.textContent = row.summary;
    elements.flagReason.textContent = row.flag_reason;
    elements.plagiarismFeatures.innerHTML = featureMarkup(row.feature_breakdown.plagiarism);
    elements.aiFeatures.innerHTML = featureMarkup(row.feature_breakdown.ai);
    elements.matchList.innerHTML = row.top_matches.length
      ? row.top_matches.map((match) => matchCard(match)).join("")
      : `<div class="pf-empty">No external matches were returned for this sentence.</div>`;
    elements.triggeredPhrases.innerHTML = row.triggered_phrases.length
      ? row.triggered_phrases.map((phrase) => `<span class="pf-pill">${escapeHtml(phrase)}</span>`).join("")
      : `<span class="pf-pill">No style-pattern phrase triggers</span>`;
    elements.triggeredCategories.innerHTML = row.triggered_categories.length
      ? row.triggered_categories.map((category) => `<span class="pf-pill">${escapeHtml(category)}</span>`).join("")
      : `<span class="pf-pill">No trigger categories</span>`;
    elements.sourceContext.textContent = row.raw_tex_context;
    elements.scoringNote.textContent =
      "Estimated risks summarize heuristic feature combinations. Review the cited evidence, neighboring prose, and manuscript context before making any determination.";
  }

  function renderExports(payload) {
    const files = payload.document.generated_files || {};
    const entries = Object.entries(files);
    if (!entries.length) {
      elements.exportActions.innerHTML = "";
      return;
    }
    elements.exportActions.innerHTML = entries
      .map(([label, href]) => {
        const text = label.toUpperCase();
        if (typeof href === "string" && /^(\/|https?:|file:|[A-Za-z]:\\)/.test(href)) {
          return `<a class="pf-button pf-button--secondary" href="${escapeAttribute(href)}" target="_blank" rel="noreferrer">${escapeHtml(
            text
          )}</a>`;
        }
        return "";
      })
      .join("");
  }

  function getVisibleRows(payload) {
    const sectionFilter = state.filters.section;
    const search = state.filters.search;
    let rows = payload.rows.filter((row) => {
      if (sectionFilter !== "all" && row.section !== sectionFilter) return false;
      if (row.plagiarism_risk_score < state.filters.plagiarism) return false;
      if (row.ai_rhetoric_risk_score < state.filters.ai) return false;
      if (state.filters.flaggedOnly && !row.is_flagged) return false;
      if (state.filters.matchesOnly && !row.has_external_match) return false;
      if (state.filters.triggersOnly && !row.has_ai_trigger) return false;
      if (search && !searchableText(row).includes(search)) return false;
      return true;
    });

    rows = rows.slice().sort((left, right) => {
      if (state.sortMode === "combined") {
        return right.combined_risk - left.combined_risk || left.order - right.order;
      }
      if (state.sortMode === "plagiarism") {
        return right.plagiarism_risk_score - left.plagiarism_risk_score || left.order - right.order;
      }
      if (state.sortMode === "ai") {
        return right.ai_rhetoric_risk_score - left.ai_rhetoric_risk_score || left.order - right.order;
      }
      return left.order - right.order;
    });
    return rows;
  }

  function getVisibleParagraphs(payload, visibleRows) {
    const visibleSet = new Set(visibleRows.map((row) => row.sentence_id));
    const paragraphs = payload.paragraphs
      .filter((paragraph) => paragraph.rows.some((row) => visibleSet.has(row.sentence_id)))
      .map((paragraph) => ({
        ...paragraph,
        rows: paragraph.rows.filter((row) => visibleSet.has(row.sentence_id)),
        sentence_ids: paragraph.rows.filter((row) => visibleSet.has(row.sentence_id)).map((row) => row.sentence_id),
      }));

    paragraphs.sort((left, right) => {
      if (state.sortMode === "combined") {
        return right.combined_risk - left.combined_risk || left.paragraph_index - right.paragraph_index;
      }
      if (state.sortMode === "plagiarism") {
        return right.plagiarism_risk_score - left.plagiarism_risk_score || left.paragraph_index - right.paragraph_index;
      }
      if (state.sortMode === "ai") {
        return right.ai_rhetoric_risk_score - left.ai_rhetoric_risk_score || left.paragraph_index - right.paragraph_index;
      }
      return left.paragraph_index - right.paragraph_index;
    });
    return paragraphs;
  }

  function ensureSelectedVisible(visibleRows, allRows) {
    if (!visibleRows.length) return;
    if (!visibleRows.some((row) => row.sentence_id === state.selectedSentenceId)) {
      state.selectedSentenceId = visibleRows[0].sentence_id;
    } else if (!findRowById(allRows, state.selectedSentenceId)) {
      state.selectedSentenceId = allRows[0].sentence_id;
    }
  }

  function selectSentence(sentenceId, scrollIntoView) {
    state.selectedSentenceId = sentenceId;
    renderDocument(state.payload);
    renderInspector(state.payload);
    if (scrollIntoView) {
      const target = elements.documentList.querySelector(`[data-sentence-id="${cssEscape(sentenceId)}"]`);
      if (target) {
        target.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    }
  }

  function jumpToParagraph(paragraphId) {
    const paragraph = state.payload.paragraphs.find((item) => item.paragraph_id === paragraphId);
    if (!paragraph || !paragraph.rows.length) return;
    selectSentence(paragraph.rows[0].sentence_id, true);
  }

  function jumpToSpan(spanId) {
    const span = state.payload.suspicious_spans.find((item) => item.span_id === spanId);
    if (!span || !span.sentence_ids.length) return;
    selectSentence(span.sentence_ids[0], true);
  }

  function handleKeydown(event) {
    if (elements.workspaceView.hidden) return;
    const target = event.target;
    if (target && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) return;
    const visibleRows = getVisibleRows(state.payload || { rows: [] });
    if (!visibleRows.length) return;
    const currentIndex = visibleRows.findIndex((row) => row.sentence_id === state.selectedSentenceId);

    if (event.altKey && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      moveBySpan(event.key === "ArrowDown" ? 1 : -1);
      return;
    }

    if (event.shiftKey && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      moveByFlagged(visibleRows, currentIndex, event.key === "ArrowDown" ? 1 : -1);
      return;
    }

    if (event.key === "ArrowDown" && currentIndex < visibleRows.length - 1) {
      event.preventDefault();
      selectSentence(visibleRows[currentIndex + 1].sentence_id, true);
      return;
    }
    if (event.key === "ArrowUp" && currentIndex > 0) {
      event.preventDefault();
      selectSentence(visibleRows[currentIndex - 1].sentence_id, true);
    }
  }

  function moveByFlagged(rows, currentIndex, direction) {
    let index = currentIndex + direction;
    while (index >= 0 && index < rows.length) {
      if (rows[index].is_flagged) {
        selectSentence(rows[index].sentence_id, true);
        return;
      }
      index += direction;
    }
  }

  function moveBySpan(direction) {
    const spans = state.payload.suspicious_spans || [];
    if (!spans.length) return;
    const currentRow = findRowById(state.payload.rows, state.selectedSentenceId);
    const currentSpanIndex = spans.findIndex((span) => currentRow && span.sentence_ids.includes(currentRow.sentence_id));
    const nextIndex = clampIndex(currentSpanIndex + direction, spans.length);
    const span = spans[nextIndex];
    if (span && span.sentence_ids.length) {
      selectSentence(span.sentence_ids[0], true);
    }
  }

  function clampIndex(index, length) {
    if (length <= 0) return 0;
    if (index < 0) return 0;
    if (index >= length) return length - 1;
    return index;
  }

  function searchableText(row) {
    return [
      row.sentence_id,
      row.section,
      row.subsection,
      row.clean_text,
      row.raw_tex_fragment,
      row.summary,
      row.source_file,
      row.top_match ? row.top_match.source_label : "",
      row.top_match ? row.top_match.matched_text : "",
    ]
      .join(" ")
      .toLowerCase();
  }

  function featureMarkup(features) {
    return features
      .map(
        (feature) => `
          <div class="pf-feature">
            <div>
              <div>${escapeHtml(feature.label)}</div>
              <div class="pf-feature__bar"><span style="width: ${Math.max(0, Math.min(100, Number(feature.value) * 100))}%;"></span></div>
            </div>
            <strong>${Number(feature.value).toFixed(2)}</strong>
          </div>
        `
      )
      .join("");
  }

  function matchCard(match) {
    const phrases = match.overlapping_phrases && match.overlapping_phrases.length
      ? `<div class="pf-pill-list" style="margin-top:10px;">${match.overlapping_phrases
          .slice(0, 5)
          .map((phrase) => `<span class="pf-pill">${escapeHtml(phrase)}</span>`)
          .join("")}</div>`
      : "";
    return `
      <div class="pf-match">
        <strong>${escapeHtml(match.source_label)}</strong>
        <div class="pf-match__meta">Vector ${Number(match.vector_similarity).toFixed(2)} · Lexical ${Number(
      match.lexical_overlap
    ).toFixed(2)} · Rare phrase ${Number(match.rare_phrase_overlap).toFixed(2)}</div>
        <div class="pf-snippet" style="margin-top:10px;">${escapeHtml(match.matched_text)}</div>
        ${phrases}
      </div>
    `;
  }

  function lineLabel(start, end) {
    return start === end ? `L${start}` : `L${start}-L${end}`;
  }

  function shortName(path) {
    return String(path || "").split(/[\\/]/).pop() || String(path || "");
  }

  function findRowById(rows, sentenceId) {
    return rows.find((row) => row.sentence_id === sentenceId) || null;
  }

  function formatFileSize(bytes) {
    if (!bytes) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let value = bytes;
    let unit = 0;
    while (value >= 1024 && unit < units.length - 1) {
      value /= 1024;
      unit += 1;
    }
    return `${value.toFixed(value >= 10 || unit === 0 ? 0 : 1)} ${units[unit]}`;
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("'", "&#39;");
  }

  function cssEscape(value) {
    if (window.CSS && window.CSS.escape) {
      return window.CSS.escape(value);
    }
    return String(value).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  init();
})();
