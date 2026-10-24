export function DetailGrid({ items }) {
  return <dl className="detail-grid">{items.map(({ label, value }) =>
    <div key={label}><dt>{label}</dt><dd>{value === null || value === undefined || value === '' ? 'No registrado' : value}</dd></div>
  )}</dl>
}
