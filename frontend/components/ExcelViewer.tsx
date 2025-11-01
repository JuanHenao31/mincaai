import React, { useState, useRef } from 'react'
import { readFileArrayBuffer, parseWorkbook, getSheetNames, sheetToRows } from '../lib/excel'

export default function ExcelViewer() {
  const [file, setFile] = useState<File | null>(null)
  const [wb, setWb] = useState<any | null>(null)
  const [sheets, setSheets] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [rows, setRows] = useState<any[][]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    const f = e.target.files?.[0] ?? null
    if (!f) return
    if (!f.name.endsWith('.xlsx')) {
      setError('Por favor sube un archivo .xlsx')
      return
    }
    setLoading(true)
    try {
      setFile(f)
      const data = await readFileArrayBuffer(f)
      const _wb = parseWorkbook(data)
      setWb(_wb)
      const names = getSheetNames(_wb)
      setSheets(names)
      const first = names[0] ?? null
      setSelected(first)
      if (first) setRows(sheetToRows(_wb, first))
    } catch (err: any) {
      console.error(err)
      setError('Error leyendo el archivo')
    } finally {
      setLoading(false)
    }
  }

  const selectSheet = (name: string) => {
    setSelected(name)
    if (!wb) return
    setRows(sheetToRows(wb, name))
  }

  const exportModified = async () => {
    setError(null)
    if (!file || !selected) {
      setError('No hay archivo o hoja seleccionada')
      return
    }
    setLoading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('sheet', selected)

      // Adjust backend URL as needed. Expecting blob (xlsx) response.
      const API_BASE = (process.env.NEXT_PUBLIC_API_BASE as string) || 'http://localhost:8000'
      const res = await fetch(`${API_BASE.replace(/\/$/, '')}/export`, {
        method: 'POST',
        body: form,
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `Error ${res.status}`)
      }
      const blob = await res.blob()
      const disposition = res.headers.get('content-disposition') || ''
      const filenameMatch = /filename="?(.*)"?/.exec(disposition)
      const filename = filenameMatch ? filenameMatch[1] : `modified-${selected}.xlsx`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Error en export')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <label style={{ display: 'block', marginBottom: 8 }}>
        Subir archivo .xlsx
        <input ref={inputRef} type="file" accept=".xlsx" onChange={onFileChange} style={{ display: 'block', marginTop: 8 }} />
      </label>

      {loading && <p>Procesando…</p>}
      {error && <p style={{ color: 'crimson' }}>{error}</p>}

      {sheets.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 12 }}>
            {sheets.map((s) => (
              <button
                key={s}
                onClick={() => selectSheet(s)}
                style={{
                  marginRight: 8,
                  padding: '6px 10px',
                  borderRadius: 6,
                  border: s === selected ? '2px solid #111827' : '1px solid #e5e7eb',
                  background: s === selected ? '#eef2ff' : 'white',
                }}
              >
                {s}
              </button>
            ))}
          </div>

          <div style={{ marginBottom: 12 }}>
            <button onClick={exportModified} disabled={loading} style={{ padding: '8px 12px', borderRadius: 6 }}>
              Export Modified Excel
            </button>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                {rows.length > 0 && (
                  <tr>
                    {rows[0].map((cell: any, idx: number) => (
                      <th key={idx} style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #e5e7eb' }}>
                        {String(cell)}
                      </th>
                    ))}
                  </tr>
                )}
              </thead>
              <tbody>
                {rows.slice(1).map((r, i) => (
                  <tr key={i}>
                    {r.map((c: any, j: number) => (
                      <td key={j} style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>
                        {String(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length === 0 && <p>No hay datos en la hoja seleccionada.</p>}
          </div>
        </div>
      )}
    </section>
  )
}
