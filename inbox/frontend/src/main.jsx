import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './contexts/ThemeContext'
import './index.css'
import './theme.css'

// 页面组件
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Strategies from './pages/Strategies'
import Accounts from './pages/Accounts'
import FundManager from './pages/FundManager'
import Instances from './pages/Instances'
import Orders from './pages/Orders'
import Positions from './pages/Positions'
import Settings from './pages/Settings'
import Notifications from './pages/Notifications'
import ThemeSettings from './pages/ThemeSettings'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="strategies" element={<Strategies />} />
            <Route path="accounts" element={<Accounts />} />
            <Route path="fund-manager" element={<FundManager />} />
            <Route path="instances" element={<Instances />} />
            <Route path="orders" element={<Orders />} />
            <Route path="positions" element={<Positions />} />
            <Route path="settings" element={<Settings />} />
            <Route path="notifications" element={<Notifications />} />
            <Route path="settings/theme" element={<ThemeSettings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
