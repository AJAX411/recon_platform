import { useContext } from 'react'
import { PendingManualContext } from './pendingContext.js'

export function usePendingManual() { return useContext(PendingManualContext) }
