import React from 'react'
import ExcelViewer from '../components/ExcelViewer'

export default function Home() {
  return (
    <main className="container">
      <h1>Excel Viewer — Demo</h1>
      <p>Sube un archivo <code>.xlsx</code>, selecciona una hoja y pruébalo.</p>
      <ExcelViewer />
    </main>
  )
}
