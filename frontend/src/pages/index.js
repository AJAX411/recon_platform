import { mountDashboard } from './DashboardPage.js'
import { mountList } from './ListPage.js'
import { mountDetail } from './DetailPage.js'
import { mountEvents } from './EventsPage.js'
import { mountIncident } from './IncidentPage.js'
import { mountPersonForm } from './PersonFormPage.js'
import { mountCreateResource } from './CreateResourcePage.js'
import { mountManual } from './ManualPage.js'

export const pages = { dashboard: mountDashboard, list: mountList, detail: mountDetail,
  events: mountEvents, alerts: mountEvents, incident: mountIncident,
  personCreate: mountPersonForm, personEdit: mountPersonForm, create: mountCreateResource, manual: mountManual }
