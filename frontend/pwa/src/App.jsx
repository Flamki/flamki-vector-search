import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { SearchBar } from "./components/SearchBar";
import { FilterChips } from "./components/FilterChips";
import { ResultGrid } from "./components/ResultGrid";

const FILTERS = ["all", "pdf", "image", "audio", "txt"];
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export default function App() {
  const [query, setQuery] = useState("sunset photo");
  const [afterDate, setAfterDate] = useState("");
  const [filter, setFilter] = useState("all");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [offline, setOffline] = useState(!navigator.onLine);

  const statusText = useMemo(() => {
    if (loading) return "Searching your local index...";
    if (error) return error;
    return `${results.length} result${results.length === 1 ? "" : "s"}`;
  }, [loading, results.length, error]);

  useEffect(() => {
    const onOffline = () => setOffline(true);
    const onOnline = () => setOffline(false);
    window.addEventListener("offline", onOffline);
    window.addEventListener("online", onOnline);
    return () => {
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("online", onOnline);
    };
  }, []);

  const runSearch = async () => {
    const q = query.trim();
    if (!q) {
      setError("Type a query to search your indexed files.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await axios.get(`${API_BASE}/search`, {
        params: {
          q,
          file_type: filter,
          top_k: 12,
          after_date: afterDate || undefined,
        },
      });
      setResults(response.data.results || []);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Search failed. Check API service and try again.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="shell">
      <div className="orb orb-a" />
      <div className="orb orb-b" />
      <section className="panel">
        <header className="hero">
          <p className={`badge ${offline ? "is-offline" : "is-online"}`}>
            <span className="dot" />
            {offline ? "OFFLINE MODE · Local stack active" : "ONLINE"}
          </p>
          <h1>Flamki Vector Search</h1>
          <p className="subtitle">Multimodal search across notes, docs, photos, and voice.</p>
        </header>

        <SearchBar
          query={query}
          onChange={setQuery}
          onSubmit={runSearch}
          loading={loading}
        />

        <div className="controls-row">
          <FilterChips filters={FILTERS} active={filter} onSelect={setFilter} />
          <label className="date-filter">
            <span>After date</span>
            <input
              type="date"
              value={afterDate}
              onChange={(e) => setAfterDate(e.target.value)}
            />
          </label>
        </div>

        <p className="status">{statusText}</p>

        <ResultGrid items={results} loading={loading} />
      </section>
    </main>
  );
}

