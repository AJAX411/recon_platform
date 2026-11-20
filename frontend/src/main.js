/** Entrada única Vanilla: carga Bootstrap/CSS local y monta la aplicación con sus páginas. */
import 'bootstrap/dist/css/bootstrap.min.css'
import './styles.css'
import { createApp } from './app.js'
import { pages } from './pages/index.js'

createApp(document.getElementById('app'), { pages })
