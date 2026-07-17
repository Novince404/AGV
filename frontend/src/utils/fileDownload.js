export function downloadTextFile(filename, payloadText, mimeType = 'application/octet-stream') {
  const blob = new Blob([payloadText], { type: mimeType })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.setTimeout(() => window.URL.revokeObjectURL(url), 0)
}

export function downloadJsonFile(filename, payloadText) {
  downloadTextFile(filename, payloadText, 'application/json;charset=utf-8')
}

export function downloadCsvFile(filename, csvText) {
  downloadTextFile(filename, csvText, 'text/csv;charset=utf-8')
}
