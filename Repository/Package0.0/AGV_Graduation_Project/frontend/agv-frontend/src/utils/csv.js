export function rowsToCsv(rows) {
  if (!rows.length) return ''

  const headers = Object.keys(rows[0])
  const escapeCsvValue = value => `"${String(value ?? '').replace(/"/g, '""')}"`
  const lines = [
    headers.map(escapeCsvValue).join(','),
    ...rows.map(row => headers.map(header => escapeCsvValue(row[header])).join(','))
  ]
  return `\ufeff${lines.join('\n')}`
}
