export function SearchBar({ query, onChange, onSubmit, loading }) {
  const onKeyDown = (event) => {
    if (event.key === "Enter") {
      onSubmit();
    }
  };

  return (
    <div className="search-wrap">
      <input
        value={query}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Try: machine learning notes, invoice march, sunset beach"
      />
      <button onClick={onSubmit} disabled={loading}>
        {loading ? "Searching..." : "Search"}
      </button>
    </div>
  );
}
