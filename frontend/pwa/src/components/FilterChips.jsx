export function FilterChips({ filters, active, onSelect }) {
  return (
    <div className="chip-row">
      {filters.map((filter) => (
        <button
          key={filter}
          onClick={() => onSelect(filter)}
          className={filter === active ? "chip active" : "chip"}
        >
          {filter.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
