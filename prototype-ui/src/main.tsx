import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Database,
  FileText,
  Gauge,
  ListChecks,
  Save,
  Search,
  Send,
  Sparkles,
} from "lucide-react";
import aesCases from "./data/aesCases.json";
import "./styles.css";

type Band = "low" | "medium" | "high";
type QueueFilter = "all" | "needs-review" | "aligned" | "completed";

type AesCase = {
  essayId: string;
  promptId: string;
  group: string;
  essayText: string;
  sourceScore: number | null;
  llmOverallScore: number | null;
  agreementGap: number | null;
  llmPerformanceBand: string | null;
  featureMeasures: {
    wordCount: number | null;
    sentenceCount: number | null;
    meanSentenceLength: number | null;
    avgWordLength: number | null;
    typeTokenRatio: number | null;
    awlRatio: number | null;
    connectiveDensity: number | null;
    lexicalOverlap: number | null;
    grammarErrors: number | null;
    grammarErrorsPer100: number | null;
    llmParagraphCount: number | null;
  };
  llmRubric: {
    organizationCoherence: number | null;
    paragraphDevelopment: number | null;
    supportingDetailElaboration: number | null;
    comprehensibility: number | null;
    promptFulfillment: number | null;
  };
  llmJustification: string;
};

type FeatureMeasure = {
  label: string;
  value: string;
  benchmark: string;
  band: Band;
};

type RubricScore = {
  label: string;
  llmScore: number | null;
  note: string;
};

type DecisionState = {
  finalScore: string;
  confidence: "high" | "medium" | "low";
  route: "accept" | "adjust" | "second-rater";
  rationale: string;
  completed: boolean;
};

const cases = aesCases as AesCase[];
const agreementThreshold = 1;

function displayNumber(value: number | null | undefined, places = 2) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "-";
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(places);
}

function isCaseAligned(item: AesCase) {
  return (item.agreementGap ?? Number.POSITIVE_INFINITY) <= agreementThreshold;
}

function statusForCase(item: AesCase, decision?: DecisionState) {
  if (decision?.completed) {
    return "Completed";
  }
  return isCaseAligned(item) ? "Aligned" : "Needs review";
}

function defaultDecision(item: AesCase): DecisionState {
  const aligned = isCaseAligned(item);
  const score = item.llmOverallScore ?? item.sourceScore ?? 0;

  return {
    finalScore: score.toString(),
    confidence: aligned ? "high" : "low",
    route: aligned ? "accept" : "adjust",
    rationale: aligned
      ? `Scores are aligned for ${item.essayId}. LLM band: ${item.llmPerformanceBand ?? "not available"}.`
      : `Scores diverge for ${item.essayId}; review feature measures and LLM justification before finalizing.`,
    completed: false,
  };
}

function bandLabel(band: Band) {
  return band === "high" ? "Strong" : band === "medium" ? "Expected" : "Review";
}

function measureBand(value: number | null, high: (value: number) => boolean, low: (value: number) => boolean): Band {
  if (typeof value !== "number") {
    return "low";
  }
  if (high(value)) {
    return "high";
  }
  return low(value) ? "low" : "medium";
}

function buildMeasures(currentCase: AesCase): FeatureMeasure[] {
  const features = currentCase.featureMeasures;

  return [
    {
      label: "Word count",
      value: displayNumber(features.wordCount, 0),
      benchmark: "Longer responses often give raters more evidence",
      band: measureBand(features.wordCount, (value) => value >= 180, (value) => value < 120),
    },
    {
      label: "Sentence count",
      value: displayNumber(features.sentenceCount, 0),
      benchmark: "Proxy for development and structure",
      band: measureBand(features.sentenceCount, (value) => value >= 8, (value) => value < 5),
    },
    {
      label: "Mean sentence length",
      value: displayNumber(features.meanSentenceLength),
      benchmark: "Expected range 15-25 words",
      band: measureBand(
        features.meanSentenceLength,
        (value) => value >= 15 && value <= 25,
        (value) => value < 10 || value > 35,
      ),
    },
    {
      label: "Type-token ratio",
      value: displayNumber(features.typeTokenRatio, 3),
      benchmark: "Lexical diversity signal",
      band: measureBand(features.typeTokenRatio, (value) => value >= 0.5, (value) => value < 0.38),
    },
    {
      label: "Connective density",
      value: `${displayNumber(features.connectiveDensity)}%`,
      benchmark: "Cohesion and transition signal",
      band: measureBand(features.connectiveDensity, (value) => value >= 5, (value) => value < 2.5),
    },
    {
      label: "Grammar issue rate",
      value: `${displayNumber(features.grammarErrorsPer100)} / 100 words`,
      benchmark: `${displayNumber(features.grammarErrors, 0)} total grammar issues`,
      band: measureBand(features.grammarErrorsPer100, (value) => value <= 3, (value) => value > 8),
    },
    {
      label: "AWL ratio",
      value: displayNumber(features.awlRatio, 3),
      benchmark: "Academic word list usage",
      band: measureBand(features.awlRatio, (value) => value >= 0.06, (value) => value < 0.02),
    },
    {
      label: "Lexical overlap",
      value: displayNumber(features.lexicalOverlap, 3),
      benchmark: "Repeated-content signal",
      band: measureBand(features.lexicalOverlap, (value) => value <= 0.12, (value) => value > 0.22),
    },
  ];
}

function buildRubricScores(currentCase: AesCase): RubricScore[] {
  return [
    {
      label: "Organization and coherence",
      llmScore: currentCase.llmRubric.organizationCoherence,
      note: "LLM rubric score for logical sequencing and paragraph coherence.",
    },
    {
      label: "Paragraph development",
      llmScore: currentCase.llmRubric.paragraphDevelopment,
      note: "LLM rubric score for whether ideas are expanded across paragraphs.",
    },
    {
      label: "Supporting detail",
      llmScore: currentCase.llmRubric.supportingDetailElaboration,
      note: "LLM rubric score for examples, reasons, and elaboration.",
    },
    {
      label: "Comprehensibility",
      llmScore: currentCase.llmRubric.comprehensibility,
      note: "LLM rubric score for reader effort and clarity.",
    },
    {
      label: "Prompt fulfillment",
      llmScore: currentCase.llmRubric.promptFulfillment,
      note: "LLM rubric score for relevance to the assigned prompt.",
    },
  ];
}

function App() {
  const [selectedEssayId, setSelectedEssayId] = useState(cases[0]?.essayId ?? "");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<QueueFilter>("all");
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>({});

  const prioritizedCases = useMemo(
    () =>
      [...cases].sort((a, b) => {
        const aGap = a.agreementGap ?? -1;
        const bGap = b.agreementGap ?? -1;
        const aNeedsReview = isCaseAligned(a) ? 0 : 1;
        const bNeedsReview = isCaseAligned(b) ? 0 : 1;
        return bNeedsReview - aNeedsReview || bGap - aGap || a.essayId.localeCompare(b.essayId);
      }),
    [],
  );

  const filteredCases = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return prioritizedCases.filter((item) => {
      const decision = decisions[item.essayId];
      const matchesQuery =
        normalizedQuery.length === 0 ||
        item.essayId.toLowerCase().includes(normalizedQuery) ||
        item.promptId.toLowerCase().includes(normalizedQuery);
      const completed = decision?.completed ?? false;
      const aligned = isCaseAligned(item);
      const matchesFilter =
        filter === "all" ||
        (filter === "completed" && completed) ||
        (filter === "aligned" && aligned && !completed) ||
        (filter === "needs-review" && !aligned && !completed);

      return matchesQuery && matchesFilter;
    });
  }, [decisions, filter, prioritizedCases, query]);

  const selectedIsVisible = filteredCases.some((item) => item.essayId === selectedEssayId);
  const currentCase = (selectedIsVisible ? filteredCases.find((item) => item.essayId === selectedEssayId) : filteredCases[0]) ?? prioritizedCases[0];
  const currentIndex = filteredCases.findIndex((item) => item.essayId === currentCase.essayId);
  const visiblePosition = currentIndex >= 0 ? currentIndex + 1 : 1;
  const currentDecision = decisions[currentCase.essayId] ?? defaultDecision(currentCase);

  const measures = useMemo(() => buildMeasures(currentCase), [currentCase]);
  const rubricScores = useMemo(() => buildRubricScores(currentCase), [currentCase]);
  const isAligned = isCaseAligned(currentCase);
  const completedCount = Object.values(decisions).filter((decision) => decision.completed).length;

  function updateDecision(patch: Partial<DecisionState>) {
    setDecisions((current) => ({
      ...current,
      [currentCase.essayId]: {
        ...(current[currentCase.essayId] ?? defaultDecision(currentCase)),
        ...patch,
      },
    }));
  }

  function moveSelection(direction: -1 | 1) {
    if (filteredCases.length === 0) {
      return;
    }
    const nextIndex = Math.min(Math.max(currentIndex + direction, 0), filteredCases.length - 1);
    setSelectedEssayId(filteredCases[nextIndex].essayId);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Review workflow">
        <div className="brand-lockup">
          <div className="brand-mark">AES</div>
          <div>
            <h1>Human Review Console</h1>
            <p>Hybrid scoring prototype</p>
          </div>
        </div>

        <nav className="workflow">
          <a className="workflow-step active" href="#essay">
            <FileText size={18} /> Essay
          </a>
          <a className="workflow-step" href="#scores">
            <Gauge size={18} /> Analysis
          </a>
          <a className="workflow-step" href="#decision">
            <ClipboardCheck size={18} /> Decision
          </a>
        </nav>

        <section className="queue-panel" aria-label="Essay review queue">
          <div className="queue-heading">
            <div>
              <div className="case-picker-heading">
                <ListChecks size={18} />
                <strong>Essay queue</strong>
              </div>
              <small>{completedCount} completed</small>
            </div>
            <span>{cases.length}</span>
          </div>

          <label className="search-field">
            <Search size={16} />
            <input
              type="search"
              placeholder="Search ID or prompt"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          <div className="filter-tabs" aria-label="Queue filters">
            {[
              ["all", "All"],
              ["needs-review", "Needs"],
              ["aligned", "Aligned"],
              ["completed", "Done"],
            ].map(([value, label]) => (
              <button
                className={filter === value ? "active" : ""}
                key={value}
                onClick={() => setFilter(value as QueueFilter)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>

          <div className="queue-list" role="list">
            {filteredCases.slice(0, 120).map((item) => {
              const decision = decisions[item.essayId];
              const status = statusForCase(item, decision);
              const selected = item.essayId === currentCase.essayId;

              return (
                <button
                  className={`queue-item ${selected ? "selected" : ""}`}
                  key={item.essayId}
                  onClick={() => setSelectedEssayId(item.essayId)}
                  type="button"
                >
                  <span>
                    <strong>{item.essayId}</strong>
                    <small>{item.promptId}</small>
                  </span>
                  <em className={`queue-status ${status.toLowerCase().replace(" ", "-")}`}>{status}</em>
                  <small>Gap {displayNumber(item.agreementGap)}</small>
                </button>
              );
            })}
            {filteredCases.length === 0 && <p className="empty-queue">No essays match this view.</p>}
          </div>

          <small>Showing {Math.min(filteredCases.length, 120)} of {filteredCases.length} matching essays.</small>
        </section>

        <div className="case-summary">
          <span>Case ID</span>
          <strong>{currentCase.essayId}</strong>
          <span>Prompt</span>
          <strong>{currentCase.promptId}</strong>
          <span>Agreement status</span>
          <strong className={isAligned ? "status-good" : "status-warning"}>{statusForCase(currentCase, currentDecision)}</strong>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Reviewer workspace</p>
            <h2>Feature analysis + LLM scoring + human final decision</h2>
          </div>
          <div className="topbar-actions">
            <div className="progress-chip">
              Essay {visiblePosition} of {filteredCases.length || cases.length}
            </div>
            <button className="icon-button" onClick={() => moveSelection(-1)} aria-label="Previous essay" title="Previous essay" disabled={currentIndex <= 0}>
              <ChevronLeft size={18} />
            </button>
            <button
              className="icon-button"
              onClick={() => moveSelection(1)}
              aria-label="Next essay"
              title="Next essay"
              disabled={currentIndex === -1 || currentIndex >= filteredCases.length - 1}
            >
              <ChevronRight size={18} />
            </button>
            <button className="icon-button" aria-label="Save draft" title="Save draft" onClick={() => updateDecision({ completed: false })}>
              <Save size={18} />
            </button>
          </div>
        </header>

        <div className="review-grid">
          <section className="panel essay-panel" id="essay">
            <div className="section-heading">
              <FileText size={20} />
              <div>
                <h3>Student Essay</h3>
                <p>
                  {currentCase.promptId} | Group {currentCase.group} | {displayNumber(currentCase.featureMeasures.wordCount, 0)} words
                </p>
              </div>
            </div>
            <article className="essay-text">
              {currentCase.essayText || "No essay text was available for this row in the joined placeholder data."}
            </article>
          </section>

          <section className="panel score-panel" id="scores">
            <div className="section-heading">
              <Gauge size={20} />
              <div>
                <h3>Scores and Measures</h3>
                <p>Signals loaded from full_sample_aes_features_with_grammar_llm_improved.xlsx.</p>
              </div>
            </div>

            <div className="score-cards">
              <div className="score-card">
                <span>Feature baseline</span>
                <strong>{displayNumber(currentCase.sourceScore)}</strong>
                <small>Temporary placeholder from score column</small>
              </div>
              <div className="score-card">
                <span>LLM evaluation</span>
                <strong>{displayNumber(currentCase.llmOverallScore)}</strong>
                <small>{currentCase.llmPerformanceBand ?? "No band"} band</small>
              </div>
              <div className={`score-card agreement ${isAligned ? "" : "needs-review"}`}>
                <span>Agreement gap</span>
                <strong>{displayNumber(currentCase.agreementGap)}</strong>
                <small>Threshold: {agreementThreshold.toFixed(2)}</small>
              </div>
            </div>

            <div className={`agreement-banner ${isAligned ? "" : "needs-review"}`}>
              {isAligned ? <CheckCircle2 size={20} /> : <AlertTriangle size={20} />}
              <div>
                <strong>
                  {isAligned
                    ? "Feature baseline and LLM scores are aligned."
                    : "Feature baseline and LLM scores diverge."}
                </strong>
                <span>Human review remains the final decision point before the score is released.</span>
              </div>
            </div>

            <div className="measure-grid">
              {measures.map((measure) => (
                <div className="measure" key={measure.label}>
                  <div>
                    <span>{measure.label}</span>
                    <strong>{measure.value}</strong>
                  </div>
                  <em className={`band ${measure.band}`}>{bandLabel(measure.band)}</em>
                  <small>{measure.benchmark}</small>
                </div>
              ))}
            </div>

            <div className="llm-justification">
              <div className="section-heading compact">
                <Database size={18} />
                <div>
                  <h3>LLM Analysis</h3>
                  <p>{currentCase.llmJustification}</p>
                </div>
              </div>
            </div>

            <div className="rubric-table" role="table" aria-label="LLM rubric scores">
              <div className="rubric-row rubric-head" role="row">
                <span>Rubric area</span>
                <span>LLM</span>
                <span>Reviewer note</span>
              </div>
              {rubricScores.map((score) => (
                <div className="rubric-row" role="row" key={score.label}>
                  <strong>{score.label}</strong>
                  <span>{displayNumber(score.llmScore, 0)}/5</span>
                  <p>{score.note}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="panel decision-panel" id="decision">
            <div className="section-heading">
              <ClipboardCheck size={20} />
              <div>
                <h3>Final Human Decision</h3>
                <p>Reviewer confirms, adjusts, or routes the case for second review.</p>
              </div>
            </div>

            <div className="decision-controls">
              <label>
                Final score
                <input
                  type="number"
                  min="0"
                  max="5"
                  step="0.25"
                  value={currentDecision.finalScore}
                  onChange={(event) => updateDecision({ finalScore: event.target.value, completed: false })}
                />
              </label>
              <label>
                Confidence
                <select
                  value={currentDecision.confidence}
                  onChange={(event) => updateDecision({ confidence: event.target.value as DecisionState["confidence"], completed: false })}
                >
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Needs second review</option>
                </select>
              </label>
            </div>

            <fieldset className="decision-options">
              <legend>Decision</legend>
              <label>
                <input
                  type="radio"
                  name={`decision-${currentCase.essayId}`}
                  checked={currentDecision.route === "accept"}
                  onChange={() => updateDecision({ route: "accept", completed: false })}
                />
                Accept aligned score
              </label>
              <label>
                <input
                  type="radio"
                  name={`decision-${currentCase.essayId}`}
                  checked={currentDecision.route === "adjust"}
                  onChange={() => updateDecision({ route: "adjust", completed: false })}
                />
                Adjust score after review
              </label>
              <label>
                <input
                  type="radio"
                  name={`decision-${currentCase.essayId}`}
                  checked={currentDecision.route === "second-rater"}
                  onChange={() => updateDecision({ route: "second-rater", confidence: "low", completed: false })}
                />
                Send to second human rater
              </label>
            </fieldset>

            <label className="notes-field">
              Rationale
              <textarea value={currentDecision.rationale} onChange={(event) => updateDecision({ rationale: event.target.value, completed: false })} />
            </label>

            <div className="decision-alert">
              <AlertTriangle size={18} />
              <span>Final decision must be submitted by a human reviewer.</span>
            </div>

            <div className="button-row">
              <button
                className="secondary-button"
                onClick={() =>
                  updateDecision({
                    rationale: `${currentDecision.rationale}\n\nDraft note: Final score ${currentDecision.finalScore}; decision route ${currentDecision.route}.`,
                    completed: false,
                  })
                }
              >
                <Sparkles size={18} /> Draft note
              </button>
              <button className="primary-button" onClick={() => updateDecision({ completed: true })}>
                <Send size={18} /> Submit decision
              </button>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
