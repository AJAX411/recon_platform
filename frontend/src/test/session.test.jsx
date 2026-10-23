import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext.jsx'
import { App } from '../App.jsx'

const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), {
  status, headers: { 'Content-Type': 'application/json', ...headers },
})

function renderApp(path) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><App /></AuthProvider></MemoryRouter>)
}

describe('rutas, sesión y permisos visuales', () => {
  it('impide abrir Personas sin sesión', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ error: 'No hay una sesión activa.' }, 401)))
    renderApp('/personas')
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Personas' })).not.toBeInTheDocument()
  })

  it('recupera la sesión al montar y oculta Personas a OPERADOR', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ id_usuario: 3, login: 'operador.ficticio', rol: 'OPERADOR' })))
    renderApp('/personas')
    expect(await screen.findByRole('heading', { name: 'Bienvenido a Recon Facial' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Personas' })).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/v1/auth/me', expect.any(Object))
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('retira el acceso cuando la API indica que la sesión expiró', async () => {
    const calls = vi.fn((url) => {
      if (url === '/api/v1/auth/me') return Promise.resolve(json({ id_usuario: 4, login: 'admin.ficticio', rol: 'ADMINISTRADOR' }))
      if (url === '/api/v1/personas/tipos') return Promise.resolve(json({ tipos: [] }))
      if (url.startsWith('/api/v1/personas?')) return Promise.resolve(json({ error: 'No hay una sesión activa.' }, 401))
      throw new Error(`Ruta de prueba inesperada: ${url}`)
    })
    vi.stubGlobal('fetch', calls)
    renderApp('/personas')
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(calls.mock.calls.some(([url]) => url.startsWith('/api/v1/personas?'))).toBe(true)
    expect(screen.queryByRole('heading', { name: 'Personas' })).not.toBeInTheDocument()
  })

  it('muestra Personas a ADMINISTRADOR y cierra sesión con CSRF', async () => {
    const calls = vi.fn().mockResolvedValueOnce(json({ id_usuario: 4, login: 'admin.ficticio', rol: 'ADMINISTRADOR' }))
      .mockResolvedValueOnce(json({ csrf_token: 'vigente' }))
      .mockResolvedValueOnce(json({ estado: 'cerrada' }))
    vi.stubGlobal('fetch', calls)
    renderApp('/')
    expect(await screen.findByRole('link', { name: 'Personas' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument())
    expect(calls.mock.calls[2][1].headers['X-CSRF-Token']).toBe('vigente')
  })

  it('inicia sesión desde el formulario con CSRF y muestra la identidad recibida', async () => {
    const calls = vi.fn().mockResolvedValueOnce(json({ error: 'No hay una sesión activa.' }, 401))
      .mockResolvedValueOnce(json({ csrf_token: 'anonimo' }))
      .mockResolvedValueOnce(json({ id_usuario: 5, login: 'admin.ficticio', rol: 'SUPERADMIN' }, 200, { 'X-CSRF-Token': 'rotado' }))
    vi.stubGlobal('fetch', calls)
    renderApp('/login')
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    await userEvent.type(screen.getByLabelText('Usuario *'), 'admin.ficticio')
    await userEvent.type(screen.getByLabelText('Contraseña *'), 'clave-ficticia')
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))
    expect(await screen.findByRole('heading', { name: 'Bienvenido a Recon Facial' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Personas' })).toBeInTheDocument()
    expect(calls.mock.calls[2][1].headers['X-CSRF-Token']).toBe('anonimo')
  })

  it('permite saltar al contenido con teclado y enfoca el contenido al cambiar de página', async () => {
    const calls = vi.fn((url) => {
      if (url === '/api/v1/auth/me') return Promise.resolve(json({ id_usuario: 4, login: 'admin.ficticio', rol: 'ADMINISTRADOR' }))
      if (url === '/api/v1/personas/tipos') return Promise.resolve(json({ tipos: [] }))
      if (url.startsWith('/api/v1/personas?')) return Promise.resolve(json({ personas: [], limite: 20, desplazamiento: 0 }))
      throw new Error(`Ruta de prueba inesperada: ${url}`)
    })
    vi.stubGlobal('fetch', calls)
    renderApp('/')
    await screen.findByRole('heading', { name: 'Bienvenido a Recon Facial' })
    await userEvent.tab()
    expect(screen.getByRole('link', { name: 'Saltar al contenido principal' })).toHaveFocus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('main')).toHaveFocus()
    await userEvent.click(screen.getByRole('link', { name: 'Personas' }))
    await screen.findByRole('heading', { name: 'Personas' })
    expect(screen.getByRole('main')).toHaveFocus()
    expect(document.title).toBe('Personas · Recon Facial')
  })
})
