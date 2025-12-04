import { useCallback, useEffect, useRef, useState } from 'react'

const trimTrailingSlash = value => (value ? value.replace(/\/+$/, '') : '')
const API_BASE = trimTrailingSlash(import.meta.env?.VITE_API_BASE || '')
const NATURE_BG = 'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1600&q=80'

const makeUrl = path => (API_BASE ? `${API_BASE}${path}` : path)

const externalUrl = path => {
  const base = API_BASE || window.location.origin
  return `${base.replace(/\/+$/, '')}${path}`
}

const defaultAuth = { token: '', username: '', role: '', user_id: '' }
const getStoredAuth = () => {
  if (typeof window === 'undefined') return defaultAuth
  try {
    const raw = window.localStorage.getItem('auth')
    if (!raw) return defaultAuth
    const parsed = JSON.parse(raw)
    if (parsed?.token) return parsed
    return defaultAuth
  } catch {
    return defaultAuth
  }
}

export default function App() {
  const [students, setStudents] = useState([])
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [usersLoading, setUsersLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ name: '', age: '', courses: '' })
  const [editId, setEditId] = useState('')
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [signupForm, setSignupForm] = useState({ username: '', password: '' })
  const [signupError, setSignupError] = useState('')
  const [showSignup, setShowSignup] = useState(false)
  const [showUsers, setShowUsers] = useState(false)
  const [userForm, setUserForm] = useState({ username: '', password: '', role: 'user' })
  const [userError, setUserError] = useState('')
  const [auth, setAuth] = useState(getStoredAuth)
  const [showIdleMessage, setShowIdleMessage] = useState(false)
  const idleTimerRef = useRef(null)

  const isAdmin = auth.role === 'admin'

  const persistAuth = useCallback(data => {
    setAuth(data)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('auth', JSON.stringify(data))
    }
  }, [])

  const handleLogout = useCallback((reason = '') => {
    setAuth(defaultAuth)
    setStudents([])
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('auth')
    }
    if (reason) {
      setShowIdleMessage(true)
      // Clear the message after 5 seconds
      setTimeout(() => setShowIdleMessage(false), 5000)
    }
  }, [])

  const resetIdleTimer = useCallback(() => {
    // Clear existing timer
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current)
      idleTimerRef.current = null
    }

    // Only set timer if user is logged in
    if (!auth.token) return

    // Set new timer for 10 minutes (600000 ms)
    idleTimerRef.current = setTimeout(() => {
      handleLogout('You have been automatically logged out due to 10 minutes of inactivity.')
      idleTimerRef.current = null
    }, 600000) // 10 minutes
  }, [auth.token, handleLogout])

  useEffect(() => {
    const body = document.body
    if (!auth.token) {
      body.classList.add('login-mode')
      // Clear idle timer when logged out
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current)
        idleTimerRef.current = null
      }
      return () => body.classList.remove('login-mode')
    }
    body.classList.remove('login-mode')
  }, [auth.token])

  // Activity tracking for idle timeout
  useEffect(() => {
    if (!auth.token) return

    // Reset timer on any user activity
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
    
    const handleActivity = () => {
      resetIdleTimer()
    }

    // Initial timer setup
    resetIdleTimer()

    // Add event listeners
    activityEvents.forEach(event => {
      document.addEventListener(event, handleActivity, true)
    })

    // Cleanup
    return () => {
      activityEvents.forEach(event => {
        document.removeEventListener(event, handleActivity, true)
      })
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current)
        idleTimerRef.current = null
      }
    }
  }, [auth.token, resetIdleTimer])

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

  const buildHeaders = useCallback(
    (headers = {}) => (auth.token ? { ...headers, Authorization: `Bearer ${auth.token}` } : headers),
    [auth.token]
  )

  const fetchWithAuth = useCallback(
    async (path, options = {}) => {
      if (!auth.token) {
        throw new Error('Please log in to continue.')
      }
      const url = makeUrl(path)
      const res = await fetch(url, {
        ...options,
        headers: buildHeaders(options.headers || {}),
      })
      if (res.status === 401) {
        handleLogout()
        throw new Error('Session expired. Please log in again.')
      }
      return res
    },
    [auth.token, buildHeaders, handleLogout]
  )

  const load = useCallback(async () => {
    if (!auth.token) return
    setLoading(true)
    setError('')
    try {
      const res = await fetchWithAuth('/api/students')
      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`Failed to load: ${res.status} ${res.statusText}. ${errorText}`)
      }
      const data = await res.json()
      setStudents(data)
    } catch (err) {
      setError(err.message || 'Failed to load students.')
    } finally {
      setLoading(false)
    }
  }, [auth.token, fetchWithAuth])

  const loadUsers = useCallback(async () => {
    if (!auth.token || !isAdmin) return
    setUsersLoading(true)
    try {
      const res = await fetchWithAuth('/api/users')
      if (!res.ok) {
        const errorText = await res.text()
        throw new Error(`Failed to load users: ${res.status} ${res.statusText}. ${errorText}`)
      }
      const data = await res.json()
      setUsers(data)
    } catch (err) {
      // Silently fail for users - not critical
    } finally {
      setUsersLoading(false)
    }
  }, [auth.token, isAdmin, fetchWithAuth])

  useEffect(() => {
    if (!auth.token) return
    load()
  }, [auth.token, load])

  useEffect(() => {
    if (!auth.token || !isAdmin) return
    loadUsers()
  }, [auth.token, isAdmin, loadUsers])

  function toCoursesArray(input) {
    const t = (input || '').trim()
    if (!t) return []
    return t.split(',').map(s => s.trim()).filter(Boolean)
  }

  async function onCreate(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        courses: toCoursesArray(form.courses),
      }
      if (!payload.name) {
        setError('Name is required')
        return
      }
      const res = await fetchWithAuth('/api/students', {
        method: 'POST',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Create failed')
      }
      const created = await res.json()
      setStudents(prev => [...prev, created])
      setForm({ name: '', age: '', courses: '' })
      setError('')
    } catch (err) {
      setError(err.message || 'Failed to create student')
    }
  }

  async function onUpdate(e) {
    e.preventDefault()
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        age: Number(form.age),
        courses: toCoursesArray(form.courses),
      }
      if (!payload.name) {
        setError('Name is required')
        return
      }
      const res = await fetchWithAuth(`/api/students/${editId}`, {
        method: 'PUT',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Update failed')
      }
      const updated = await res.json()
      setStudents(prev => prev.map(s => (s.id === editId ? updated : s)))
      setEditId('')
      setForm({ name: '', age: '', courses: '' })
      setError('')
    } catch (err) {
      setError(err.message || 'Failed to update student')
    }
  }

  async function onDelete(id) {
    if (!confirm('Are you sure you want to delete this student?')) return
    setError('')
    try {
      const res = await fetchWithAuth(`/api/students/${id}`, { method: 'DELETE' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Delete failed')
      }
      setStudents(prev => prev.filter(s => s.id !== id))
    } catch (err) {
      setError(err.message || 'Failed to delete student')
    }
  }

  async function onCreateUser(e) {
    e.preventDefault()
    setUserError('')
    const username = userForm.username.trim()
    const password = userForm.password
    
    if (password.length < 3) {
      setUserError('Password must be at least 3 characters')
      return
    }
    if (username.length < 3) {
      setUserError('Username must be at least 3 characters')
      return
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setUserError('Username can only contain letters, numbers, and underscores')
      return
    }
    
    try {
      const res = await fetchWithAuth('/api/users', {
        method: 'POST',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ username, password, role: userForm.role }),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to create user')
      }
      const created = await res.json()
      setUsers(prev => [...prev, created])
      setUserForm({ username: '', password: '', role: 'user' })
      setUserError('')
    } catch (err) {
      setUserError(err.message || 'Failed to create user')
    }
  }

  function startEditUser(user) {
    setEditUserId(user.id)
    setUserForm({
      username: user.username,
      password: '',
      role: user.role
    })
  }

  async function onUpdateUser(e) {
    e.preventDefault()
    setUserError('')
    const updateData = {}
    if (userForm.username.trim()) updateData.username = userForm.username.trim()
    if (userForm.password) updateData.password = userForm.password
    if (userForm.role) updateData.role = userForm.role
    
    if (Object.keys(updateData).length === 0) {
      setUserError('Please provide at least one field to update')
      return
    }
    
    try {
      const res = await fetchWithAuth(`/api/users/${editUserId}`, {
        method: 'PUT',
        headers: buildHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(updateData),
      })
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to update user')
      }
      const updated = await res.json()
      setUsers(prev => prev.map(u => u.id === editUserId ? updated : u))
      setEditUserId('')
      setUserForm({ username: '', password: '', role: 'user' })
      setUserError('')
    } catch (err) {
      setUserError(err.message || 'Failed to update user')
    }
  }

  async function onDeleteUser(userId) {
    if (!confirm('Are you sure you want to delete this user?')) return
    setUserError('')
    try {
      const res = await fetchWithAuth(`/api/users/${userId}`, { method: 'DELETE' })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || 'Delete failed')
      }
      setUsers(prev => prev.filter(u => u.id !== userId))
    } catch (err) {
      setUserError(err.message || 'Failed to delete user')
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

  async function handleLogin(e) {
    e.preventDefault()
    setLoginError('')
    try {
      const res = await fetch(makeUrl('/api/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginForm.username.trim(),
          password: loginForm.password,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed')
      }
      const session = { token: data.token, username: data.username, role: data.role, user_id: data.user_id }
      persistAuth(session)
      setLoginForm({ username: '', password: '' })
      setError('')
      setShowIdleMessage(false)
    } catch (err) {
      setLoginError(err.message || 'Login failed')
    }
  }

  async function handleSignup(e) {
    e.preventDefault()
    setSignupError('')
    const username = signupForm.username.trim()
    const password = signupForm.password
    
    // Frontend validation
    if (password.length < 3) {
      setSignupError('Password must be at least 3 characters')
      return
    }
    if (username.length < 3) {
      setSignupError('Username must be at least 3 characters')
      return
    }
    // Validate username format (alphanumeric and underscore only)
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setSignupError('Username can only contain letters, numbers, and underscores')
      return
    }
    
    try {
      const res = await fetch(makeUrl('/api/signup'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.detail || 'Signup failed')
      }
      const session = { token: data.token, username: data.username, role: data.role, user_id: data.user_id }
      persistAuth(session)
      setSignupForm({ username: '', password: '' })
      setShowSignup(false)
      setError('')
      setShowIdleMessage(false)
    } catch (err) {
      setSignupError(err.message || 'Signup failed')
    }
  }

  if (!auth.token) {
    return (
      <div className="login-page" style={{ backgroundImage: `linear-gradient(rgba(15,23,42,0.6), rgba(15,23,42,0.6)), url('${NATURE_BG}')` }}>
        {showIdleMessage && (
          <div className="idle-message">
            <div className="idle-message-content">
              <h3>Session Expired</h3>
              <p>You have been automatically logged out due to 10 minutes of inactivity.</p>
              <p>Please sign in again to continue.</p>
            </div>
          </div>
        )}
        <div className="login-card">
          <h1>School Portal</h1>
          {!showSignup ? (
            <>
              <p>Sign in to manage students.</p>
              {loginError ? <div className="login-error">{loginError}</div> : null}
              <form className="login-form" onSubmit={handleLogin}>
                <input
                  className="login-input"
                  placeholder="Username"
                  value={loginForm.username}
                  onChange={e => setLoginForm({ ...loginForm, username: e.target.value })}
                  required
                />
                <input
                  className="login-input"
                  type="password"
                  placeholder="Password"
                  value={loginForm.password}
                  onChange={e => setLoginForm({ ...loginForm, password: e.target.value })}
                  required
                />
                <button className="btn btn-primary" type="submit">Login</button>
              </form>
              <div className="login-switch">
                <p>Don't have an account? <button type="button" className="link-btn" onClick={() => { setShowSignup(true); setLoginError('') }}>Sign up</button></p>
              </div>
            </>
          ) : (
            <>
              <p>Create a new account to manage students.</p>
              {signupError ? <div className="login-error">{signupError}</div> : null}
              <form className="login-form" onSubmit={handleSignup}>
                <input
                  className="login-input"
                  placeholder="Username (min 3 characters, letters/numbers/_ only)"
                  value={signupForm.username}
                  onChange={e => setSignupForm({ ...signupForm, username: e.target.value })}
                  minLength={3}
                  maxLength={50}
                  pattern="^[a-zA-Z0-9_]+$"
                  required
                />
                <input
                  className="login-input"
                  type="password"
                  placeholder="Password (min 3 characters)"
                  value={signupForm.password}
                  onChange={e => setSignupForm({ ...signupForm, password: e.target.value })}
                  minLength={3}
                  required
                />
                <button className="btn btn-primary" type="submit">Sign up</button>
              </form>
              <div className="login-switch">
                <p>Already have an account? <button type="button" className="link-btn" onClick={() => { setShowSignup(false); setSignupError('') }}>Sign in</button></p>
              </div>
            </>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="header">
        <div>
          <h1 className="title">Students</h1>
          <p className="subtitle">Manage students and their courses</p>
        </div>
        <div className="toolbar">
          {isAdmin && (
            <>
              <button className="btn" onClick={() => setShowUsers(!showUsers)}>
                {showUsers ? 'Hide Users' : 'Manage Users'}
              </button>
              <button className="btn" onClick={() => window.open(externalUrl('/health'), '_blank')}>Health</button>
              <button className="btn" onClick={() => window.open(externalUrl('/api/students'), '_blank')}>List JSON</button>
              <button className="btn" onClick={() => window.open(externalUrl('/docs'), '_blank')}>OpenAPI Docs</button>
              <button className="btn" onClick={() => window.open(externalUrl('/redoc'), '_blank')}>ReDoc</button>
            </>
          )}
        </div>
      </div>

      <div className="user-chip">
        <div>
          Signed in as <strong>{auth.username}</strong> ({auth.role})
          {!isAdmin ? <span className="user-note">Limited access</span> : null}
        </div>
        <button className="btn" onClick={handleLogout}>Logout</button>
      </div>

      {error ? <div className="notice">{error}</div> : null}

      {isAdmin && showUsers && (
        <div className="card panel" style={{ marginBottom: 24 }}>
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>User Management</h2>
          {userError ? <div className="notice" style={{ marginBottom: 16, background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: '#991b1b' }}>{userError}</div> : null}
          
          {!editUserId ? (
            <form onSubmit={onCreateUser} className="form-grid" style={{ marginBottom: 16 }}>
              <input
                className="input"
                placeholder="Username (min 3 chars)"
                value={userForm.username}
                onChange={e => setUserForm({ ...userForm, username: e.target.value })}
                minLength={3}
                maxLength={50}
                pattern="^[a-zA-Z0-9_]+$"
                required
              />
              <input
                className="input"
                type="password"
                placeholder="Password (min 3 chars)"
                value={userForm.password}
                onChange={e => setUserForm({ ...userForm, password: e.target.value })}
                minLength={3}
                required
              />
              <select
                className="input"
                value={userForm.role}
                onChange={e => setUserForm({ ...userForm, role: e.target.value })}
                style={{ padding: '10px 12px' }}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <button className="btn btn-primary" type="submit">Add User</button>
            </form>
          ) : (
            <form onSubmit={onUpdateUser} className="form-grid" style={{ marginBottom: 16 }}>
              <input
                className="input"
                placeholder="Username (min 3 chars)"
                value={userForm.username}
                onChange={e => setUserForm({ ...userForm, username: e.target.value })}
                minLength={3}
                maxLength={50}
                pattern="^[a-zA-Z0-9_]+$"
                required
              />
              <input
                className="input"
                type="password"
                placeholder="New password (leave empty to keep current)"
                value={userForm.password}
                onChange={e => setUserForm({ ...userForm, password: e.target.value })}
                minLength={3}
              />
              <select
                className="input"
                value={userForm.role}
                onChange={e => setUserForm({ ...userForm, role: e.target.value })}
                style={{ padding: '10px 12px' }}
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
              <button className="btn btn-primary" type="submit">Update User</button>
              <button className="btn" type="button" onClick={() => { setEditUserId(''); setUserForm({ username: '', password: '', role: 'user' })}}>Cancel</button>
            </form>
          )}

          {usersLoading ? (
            <div>Loading users...</div>
          ) : users.length === 0 ? (
            <div className="notice">No users found.</div>
          ) : (
            <table className="table">
              <thead className="thead">
                <tr>
                  <th className="th">Username</th>
                  <th className="th">Role</th>
                  <th className="th">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td className="td">{u.username}</td>
                    <td className="td">
                      <span style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: '999px',
                        fontSize: '12px',
                        background: u.role === 'admin' ? '#dbeafe' : '#f3f4f6',
                        color: u.role === 'admin' ? '#1e40af' : '#374151'
                      }}>
                        {u.role}
                      </span>
                    </td>
                    <td className="td">
                      <div className="actions">
                        {u.id !== auth.user_id ? (
                          <>
                            <button className="btn" onClick={() => startEditUser(u)}>Edit</button>
                            <button className="btn btn-danger" onClick={() => onDeleteUser(u.id)}>Delete</button>
                          </>
                        ) : (
                          <span style={{ color: 'var(--muted)', fontSize: '14px' }}>Current user</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

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
              {isAdmin && <th className="th">Added by</th>}
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
                {isAdmin && (
                  <td className="td">{s.owner_username || 'Unknown'}</td>
                )}
                <td className="td">
                  <div className="actions">
                    <button className="btn" onClick={() => startEdit(s)}>Edit</button>
                    <button className="btn btn-danger" onClick={() => onDelete(s.id)}>Delete</button>
                    {isAdmin ? (
                      <button className="btn" onClick={() => window.open(externalUrl(`/api/students/${s.id}`), '_blank')}>View JSON</button>
                    ) : null}
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
