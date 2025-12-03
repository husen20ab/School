import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

const API_BASE = trimTrailingSlash(import.meta.env?.VITE_API_BASE || '')
const makeUrl = path => (API_BASE ? `${API_BASE}${path}` : path)

const handleSignup = async (e, username, password) => {
  e.preventDefault()
  const response = await fetch(makeUrl('/api/signup'), {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
  if (!response.ok) {
    const error = await response.text()
    setError(error)
  } else {
    navigate('/')
  }
}
export default function Signup() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()
  return (
    <div>
      <h1>Sign up</h1>
      <p>Create an account to manage students.</p>
      <form onSubmit={e => handleSignup(e, username, password)}>
        <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required />
        <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
        <button type="submit">Sign up</button>
      </form>
      {error ? <div className="error">{error}</div> : null}
    </div>
  )
}