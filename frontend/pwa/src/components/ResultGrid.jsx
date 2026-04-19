function scoreLabel(score) {
  if (typeof score !== "number") return "N/A";
  return score.toFixed(3);
}

function snippet(text) {
  if (!text) return "No text snippet available.";
  return text.length > 180 ? `${text.slice(0, 177)}...` : text;
}

function ResultCard({ item }) {
  const meta = item.meta || {};
  return (
    <article className="card">
      <div className="card-head">
        <h3>{meta.file_name || "Untitled"}</h3>
        <span>{meta.file_type || meta.modality || "unknown"}</span>
      </div>
      <p className="path" title={meta.path}>{meta.path}</p>
      <p className="snippet">{snippet(meta.content)}</p>
      <div className="card-foot">
        <small>{meta.stream || "hybrid"}</small>
        <small>score {scoreLabel(item.score)}</small>
      </div>
    </article>
  );
}

export function ResultGrid({ items, loading }) {
  if (loading) {
    return (
      <div className="grid skeleton-grid">
        {Array.from({ length: 6 }).map((_, idx) => (
          <div key={idx} className="card skeleton" />
        ))}
      </div>
    );
  }

  if (!items.length) {
    return <p className="empty">No matches yet. Try a broader query or change filters.</p>;
  }

  return (
    <div className="grid">
      {items.map((item) => (
        <ResultCard key={item.id} item={item} />
      ))}
    </div>
  );
}
