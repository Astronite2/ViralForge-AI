import { useEffect, useMemo, useState } from "react";
import "./App.css";

type Topic = {
  id: string;
  display_name: string;
  normalized_key: string;
  created_at: string;
};

type Signal = {
  id: string;
  topic_id: string;
  topic_name: string;
  source: string;
  score: number;
  confidence: number;
  reason: string;
  timestamp: string;
  correlation_id: string;
  created_at: string;
};

type Evidence = {
  id: string;
  source: string;
  factor: string;
  raw_value: number;
  normalized_value: number;
  weight: number;
  contribution: number;
  confidence: number;
  reason: string;
  timestamp: string;
  signal_id: string;
};

type Explanation = {
  factor: string;
  weight: number;
  contribution: number;
  confidence: number;
  reason: string;
};

type Decision = {
  id: string;
  topic_id: string;
  topic_name: string;
  decision_type: string;
  score: number;
  confidence: number;
  summary: string;
  recommended_action: string;
  created_at: string;
  engine_version: string;
  event_version: string;
  correlation_id: string;
  weights_snapshot: Record<string, number>;
  evidence: Evidence[];
  explanations: Explanation[];
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatSource(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function App() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [selectedDecisionId, setSelectedDecisionId] = useState<string | null>(
    null,
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadDashboard(): Promise<void> {
    try {
      setLoading(true);
      setError(null);

      const [topicData, signalData, decisionData] = await Promise.all([
        fetchJson<Topic[]>("/api/v1/topics"),
        fetchJson<Signal[]>("/api/v1/signals"),
        fetchJson<Decision[]>("/api/v1/decisions"),
      ]);

      setTopics(topicData);
      setSignals(signalData);
      setDecisions(decisionData);

      if (decisionData.length > 0) {
        setSelectedDecisionId((current) => current ?? decisionData[0].id);
      }
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Unable to load dashboard data.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, []);

  const selectedDecision = useMemo(() => {
    return (
      decisions.find((decision) => decision.id === selectedDecisionId) ??
      decisions[0] ??
      null
    );
  }, [decisions, selectedDecisionId]);

  const averageScore = useMemo(() => {
    if (decisions.length === 0) {
      return 0;
    }

    return (
      decisions.reduce((total, decision) => total + decision.score, 0) /
      decisions.length
    );
  }, [decisions]);

  const averageConfidence = useMemo(() => {
    if (decisions.length === 0) {
      return 0;
    }

    return (
      decisions.reduce((total, decision) => total + decision.confidence, 0) /
      decisions.length
    );
  }, [decisions]);

  const createDecisions = decisions.filter(
    (decision) => decision.decision_type.toLowerCase() === "create",
  ).length;

  if (loading) {
    return (
      <main className="state-page">
        <div className="loader" />
        <p>Loading ViralForge intelligence…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="state-page">
        <div className="error-card">
          <h1>Dashboard unavailable</h1>
          <p>{error}</p>
          <button type="button" onClick={() => void loadDashboard()}>
            Retry
          </button>
        </div>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <div className="brand-mark">V</div>
          <div className="brand-copy">
            <strong>ViralForge</strong>
            <span>Decision Intelligence</span>
          </div>
        </div>

        <nav>
          <a className="active" href="#overview">
            Overview
          </a>
          <a href="#decisions">Decisions</a>
          <a href="#signals">Signals</a>
          <a href="#evidence">Evidence</a>
        </nav>

        <div className="sidebar-status">
          <span className="status-dot" />
          Backend connected
        </div>
      </aside>

      <main className="dashboard">
        <header className="topbar">
          <div>
            <p className="eyebrow">Intelligence overview</p>
            <h1>What should you create next?</h1>
            <p>
              Evidence-backed content opportunities generated by the ViralForge
              decision engine.
            </p>
          </div>

          <button
            className="refresh-button"
            type="button"
            onClick={() => void loadDashboard()}
          >
            Refresh intelligence
          </button>
        </header>

        <section id="overview" className="metrics-grid">
          <article className="metric-card">
            <span>Topics</span>
            <strong>{topics.length}</strong>
            <small>Tracked opportunities</small>
          </article>

          <article className="metric-card">
            <span>Signals</span>
            <strong>{signals.length}</strong>
            <small>Evidence sources detected</small>
          </article>

          <article className="metric-card">
            <span>Create decisions</span>
            <strong>{createDecisions}</strong>
            <small>Recommended actions</small>
          </article>

          <article className="metric-card">
            <span>Average score</span>
            <strong>{averageScore.toFixed(1)}</strong>
            <small>{averageConfidence.toFixed(1)}% confidence</small>
          </article>
        </section>

        {selectedDecision ? (
          <>
            <section className="hero-grid">
              <article className="opportunity-card">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Top opportunity</p>
                    <h2>{selectedDecision.topic_name}</h2>
                  </div>

                  <span
                    className={`decision-badge ${selectedDecision.decision_type.toLowerCase()}`}
                  >
                    {selectedDecision.decision_type}
                  </span>
                </div>

                <p className="opportunity-summary">
                  {selectedDecision.summary}
                </p>

                <div className="score-row">
                  <div>
                    <span>Decision score</span>
                    <strong>{selectedDecision.score.toFixed(1)}</strong>
                  </div>

                  <div>
                    <span>Confidence</span>
                    <strong>{selectedDecision.confidence.toFixed(1)}%</strong>
                  </div>
                </div>

                <div className="progress-track">
                  <div
                    className="progress-value"
                    style={{ width: `${selectedDecision.score}%` }}
                  />
                </div>

                <div className="recommended-action">
                  <span>Recommended action</span>
                  <strong>{selectedDecision.recommended_action}</strong>
                </div>
              </article>

              <article className="trace-card">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Traceability</p>
                    <h2>Decision record</h2>
                  </div>
                </div>

                <dl>
                  <div>
                    <dt>Engine version</dt>
                    <dd>{selectedDecision.engine_version}</dd>
                  </div>
                  <div>
                    <dt>Event version</dt>
                    <dd>{selectedDecision.event_version}</dd>
                  </div>
                  <div>
                    <dt>Correlation ID</dt>
                    <dd>{selectedDecision.correlation_id}</dd>
                  </div>
                  <div>
                    <dt>Calculated</dt>
                    <dd>{formatDate(selectedDecision.created_at)}</dd>
                  </div>
                </dl>
              </article>
            </section>

            <section id="evidence" className="panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Evidence breakdown</p>
                  <h2>Why ViralForge made this decision</h2>
                </div>
              </div>

              <div className="evidence-list">
                {selectedDecision.explanations.map((explanation) => (
                  <article
                    className="evidence-item"
                    key={explanation.factor}
                  >
                    <div className="evidence-header">
                      <div>
                        <strong>{explanation.factor}</strong>
                        <span>
                          Weight {(explanation.weight * 100).toFixed(0)}%
                        </span>
                      </div>

                      <strong className="contribution">
                        +{explanation.contribution.toFixed(1)}
                      </strong>
                    </div>

                    <div className="evidence-bar">
                      <div
                        style={{
                          width: `${Math.min(
                            100,
                            explanation.contribution * 3.33,
                          )}%`,
                        }}
                      />
                    </div>

                    <p>{explanation.reason}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="two-column-grid">
              <article id="signals" className="panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Latest signals</p>
                    <h2>Evidence entering the engine</h2>
                  </div>
                </div>

                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Topic</th>
                        <th>Source</th>
                        <th>Score</th>
                        <th>Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {signals.map((signal) => (
                        <tr key={signal.id}>
                          <td>
                            <strong>{signal.topic_name}</strong>
                            <small>{formatDate(signal.timestamp)}</small>
                          </td>
                          <td>{formatSource(signal.source)}</td>
                          <td>{signal.score.toFixed(2)}</td>
                          <td>{(signal.confidence * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </article>

              <article id="decisions" className="panel">
                <div className="section-heading">
                  <div>
                    <p className="eyebrow">Decision history</p>
                    <h2>Recommendations</h2>
                  </div>
                </div>

                <div className="decision-list">
                  {decisions.map((decision) => (
                    <button
                      className={
                        decision.id === selectedDecision.id
                          ? "decision-row selected"
                          : "decision-row"
                      }
                      key={decision.id}
                      type="button"
                      onClick={() => setSelectedDecisionId(decision.id)}
                    >
                      <div>
                        <strong>{decision.topic_name}</strong>
                        <span>{formatDate(decision.created_at)}</span>
                      </div>

                      <div>
                        <span
                          className={`decision-badge ${decision.decision_type.toLowerCase()}`}
                        >
                          {decision.decision_type}
                        </span>
                        <strong>{decision.score.toFixed(1)}</strong>
                      </div>
                    </button>
                  ))}
                </div>
              </article>
            </section>
          </>
        ) : (
          <section className="empty-state">
            <h2>No intelligence available</h2>
            <p>
              Run the intelligence pipeline to generate topics, signals, and
              decisions.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
