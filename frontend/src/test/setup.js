import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { clearCsrf } from '../api/http.js'

afterEach(() => { cleanup(); clearCsrf(); vi.restoreAllMocks() })
