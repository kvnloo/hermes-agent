export function validateInteractionEvidence(trace) {
  const expectedWidths = [320, 360, 390, 430, 1220]
  if (!Array.isArray(trace.responsiveTrace)) throw new Error('missing responsive interaction trace')
  for (const width of expectedWidths) {
    const row = trace.responsiveTrace.find(candidate => candidate.width === width)
    if (!row?.escapeFocusRestored) throw new Error(`missing Escape focus proof at ${width}px`)
    if (!row?.cancelFocusRestored) throw new Error(`missing Cancel focus proof at ${width}px`)
    if (!Array.isArray(row.openGeometry?.controls) || row.openGeometry.controls.length === 0) throw new Error(`missing open-state geometry at ${width}px`)
  }
}