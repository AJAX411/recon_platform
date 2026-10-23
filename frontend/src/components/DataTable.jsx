export function DataTable({ caption, columns, children }) {
  return <div className="table-responsive"><table className="table people-table">
    <caption className="visually-hidden">{caption}</caption>
    <thead><tr>{columns.map((column) => <th key={column} scope="col">{column}</th>)}</tr></thead>
    <tbody>{children}</tbody>
  </table></div>
}
