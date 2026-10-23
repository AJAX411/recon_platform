export function Field({ id, label, error, required, ...props }) {
  return <div className="mb-3">
    <label className="form-label" htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label>
    <input id={id} name={id} className={`form-control${error ? ' is-invalid' : ''}`}
      required={required} aria-required={required || undefined}
      aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} {...props} />
    {error && <div id={`${id}-error`} className="invalid-feedback">{error}</div>}
  </div>
}

export function SelectField({ id, label, children, error, required, ...props }) {
  return <div className="mb-3">
    <label className="form-label" htmlFor={id}>{label}{required && <span aria-hidden="true"> *</span>}</label>
    <select id={id} name={id} className={`form-select${error ? ' is-invalid' : ''}`}
      required={required} aria-required={required || undefined}
      aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} {...props}>{children}</select>
    {error && <div id={`${id}-error`} className="invalid-feedback">{error}</div>}
  </div>
}
