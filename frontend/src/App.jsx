import { useEffect, useState } from 'react'

const trimTrailingSlash = value => (value ? value.replace(/\/+$/, '') : '')
const API_BASE = trimTrailingSlash(import.meta.env?.VITE_API_BASE || '')

const makeUrl = path => {
  if (API_BASE) return `${API_BASE}${path}`
  return path
}

const externalUrl = path => {
  const base = API_BASE || window.location.origin
  return `${base.replace(/\/+$/, '')}${path}`
}

const api = {
  async getStudent(id) {
    const res = await fetch(makeUrl(`/api/students/${id}`))
    if (!res.ok) throw new Error('Not found')
    return res.json()
  },
  async createStudent(payload) {
    const res = await fetch(makeUrl(`/api/students`), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Create failed')
    return res.json()
  },
  async updateStudent(id, payload) {
    const res = await fetch(makeUrl(`/api/students/${id}`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!res.ok) throw new Error('Update failed')
    return res.json()
  },
  async deleteStudent(id) {
    const res = await fetch(makeUrl(`/api/students/${id}`), { method: 'DELETE' })
    if (!res.ok) throw new Error('Delete failed')
  },
}

export default function App() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', age: '', courses: '' })
  const [editId, setEditId] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(makeUrl('/api/students'))
      if (!res.ok) throw new Error('Failed to load')
      const data = await res.json()
      setStudents(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    const bgUrl = import.meta.env?.VITE_BG_URL
    if (!bgUrl) return undefined
    const root = document.documentElement
    const previous = getComputedStyle(root).getPropertyValue('--custom-bg')
    root.style.setProperty('--custom-bg', `url('${bgUrl}')`)
    return () => {
      if (previous) {
        root.style.setProperty('--custom-bg', previous)
      } else {
        root.style.removeProperty('--custom-bg')
      }
    }
  }, [])

  function toCoursesArray(input) {
    const t = (input || '').trim()
    if (!t) return []
    return t.split(',').map(s => s.trim()).filter(Boolean)
  }

  async function onCreate(e) {
    e.preventDefault()
    try {
      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        courses: toCoursesArray(form.courses),
      }
      const created = await api.createStudent(payload)
      setStudents(prev => [...prev, created])
      setForm({ name: '', age: '', courses: '' })
    } catch (err) {
      setError(err.message)
    }
  }

  function startEdit(s) {
    setEditId(s.id)
    setForm({
      name: s.name,
      age: String(s.age),
      courses: (s.courses || []).join(', '),
    })
  }

  async function onUpdate(e) {
    e.preventDefault()
    try {
      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        courses: toCoursesArray(form.courses),
      }
      const updated = await api.updateStudent(editId, payload)
      setStudents(prev => prev.map(s => (s.id === editId ? updated : s)))
      setEditId('')
      setForm({ name: '', age: '', courses: '' })
    } catch (err) {
      setError(err.message)
    }
  }

  async function onDelete(id) {
    try {
      await api.deleteStudent(id)
      setStudents(prev => prev.filter(s => s.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1 className="title">Students</h1>
          <p className="subtitle">Manage students and their courses</p>
        </div>
        <div className="toolbar">
          <button className="btn" onClick={() => window.open(externalUrl('/health'), '_blank')}>Health</button>
          <button className="btn" onClick={() => window.open(externalUrl('/api/students'), '_blank')}>List JSON</button>
          <button className="btn" onClick={() => window.open(externalUrl('/docs'), '_blank')}>OpenAPI Docs</button>
          <button className="btn" onClick={() => window.open(externalUrl('/redoc'), '_blank')}>ReDoc</button>
        </div>
      </div>
      {error ? <div className="notice">{error}</div> : null}

      {!editId ? (
        <form onSubmit={onCreate} className="card panel form-grid" style={{ marginBottom: 16 }}>
          <input className="input" placeholder="Name" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <input className="input" type="number" min="0" placeholder="Age" required value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} />
          <input className="input" placeholder="Courses (comma separated)" value={form.courses} onChange={e => setForm({ ...form, courses: e.target.value })} />
          <button className="btn btn-primary" type="submit">Add</button>
        </form>
      ) : (
        <form onSubmit={onUpdate} className="card panel form-grid" style={{ marginBottom: 16 }}>
          <input className="input" placeholder="Name" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <input className="input" type="number" min="0" placeholder="Age" required value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} />
          <input className="input" placeholder="Courses (comma separated)" value={form.courses} onChange={e => setForm({ ...form, courses: e.target.value })} />
          <button className="btn btn-primary" type="submit">Update</button>
          <button className="btn" type="button" onClick={() => { setEditId(''); setForm({ name: '', age: '', courses: '' })}}>Cancel</button>
        </form>
      )}

      {loading ? <div className="card panel">Loading...</div> : null}

      {students.length === 0 ? (
        <div className="card panel notice">No students yet. Add one above.</div>
      ) : (
        <table className="card panel table">
          <thead className="thead">
            <tr>
              <th className="th">ID</th>
              <th className="th">Name</th>
              <th className="th">Age</th>
              <th className="th">Courses</th>
              <th className="th">Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map(s => (
              <tr key={s.id}>
                <td className="td">{s.id}</td>
                <td className="td">{s.name}</td>
                <td className="td">{s.age}</td>
                <td className="td">{(s.courses || []).join(', ')}</td>
                <td className="td">
                  <div className="actions">
                    <button className="btn" onClick={() => startEdit(s)}>Edit</button>
                    <button className="btn btn-danger" onClick={() => onDelete(s.id)}>Delete</button>
                    <button className="btn" onClick={() => window.open(externalUrl(`/api/students/${s.id}`), '_blank')}>View JSON</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

