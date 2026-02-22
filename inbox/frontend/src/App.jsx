import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import ThemeToggle from './components/ThemeToggle';
import { 
  HomeIcon, 
  RocketLaunchIcon, 
  UserGroupIcon, 
  DocumentTextIcon,
  ShoppingCartIcon,
  CubeIcon,
  CurrencyDollarIcon,
  BellIcon,
  Cog6ToothIcon,
  PaintBrushIcon,
  Bars3Icon,
  XMarkIcon
} from '@heroicons/react/24/outline';

// 导入所有页面组件
import Dashboard from './pages/Dashboard';
import Instances from './pages/Instances';
import Accounts from './pages/Accounts';
import Strategies from './pages/Strategies';
import Orders from './pages/Orders';
import Positions from './pages/Positions';
import FundManager from './pages/FundManager';
import Notifications from './pages/Notifications';
import Settings from './pages/Settings';
import ThemeSettings from './pages/ThemeSettings';
import Symbols from './pages/Symbols';
import System from './pages/System';

import './theme.css';

// 导航菜单配置
const navigationConfig = [
  {
    name: '仪表盘',
    path: '/',
    icon: HomeIcon,
    exact: true
  },
  {
    name: '交易管理',
    items: [
      { name: '交易实例', path: '/instances', icon: RocketLaunchIcon },
      { name: '策略管理', path: '/strategies', icon: DocumentTextIcon },
      { name: '订单管理', path: '/orders', icon: ShoppingCartIcon },
      { name: '持仓管理', path: '/positions', icon: CubeIcon }
    ]
  },
  {
    name: '资金管理',
    items: [
      { name: '资金配置', path: '/fund-manager', icon: CurrencyDollarIcon }
    ]
  },
  {
    name: '系统管理',
    items: [
      { name: '账户管理', path: '/accounts', icon: UserGroupIcon },
      { name: '交易对管理', path: '/symbols', icon: CubeIcon },
      { name: '系统监控', path: '/system', icon: Cog6ToothIcon },
      { name: '通知管理', path: '/notifications', icon: BellIcon },
      { name: '系统设置', path: '/settings', icon: Cog6ToothIcon },
      { name: '主题设置', path: '/settings/theme', icon: PaintBrushIcon }
    ]
  }
];

function Sidebar({ isOpen, onClose }) {
  const location = useLocation();

  const isActive = (path, exact = false) => {
    if (exact) {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  return (
    <>
      {/* 移动端遮罩 */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}
      
      {/* 侧边栏 */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-64 transform transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:z-0
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        style={{ 
          backgroundColor: 'var(--color-bg-secondary)',
          borderRight: '1px solid var(--color-border-primary)'
        }}
      >
        <div className="flex flex-col h-full">
          {/* Logo和关闭按钮 */}
          <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--color-border-primary)' }}>
            <h1 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
              交易机器人
            </h1>
            <button
              onClick={onClose}
              className="lg:hidden p-2 rounded-md hover:bg-opacity-10"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {/* 导航菜单 */}
          <nav className="flex-1 overflow-y-auto p-4 space-y-6">
            {navigationConfig.map((section, idx) => (
              <div key={idx}>
                {section.path ? (
                  // 单个链接
                  <Link
                    to={section.path}
                    onClick={onClose}
                    className={`
                      flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors
                      ${isActive(section.path, section.exact) 
                        ? 'bg-opacity-10' 
                        : 'hover:bg-opacity-5'
                      }
                    `}
                    style={{
                      color: isActive(section.path, section.exact) 
                        ? 'var(--color-accent-primary)' 
                        : 'var(--color-text-primary)',
                      backgroundColor: isActive(section.path, section.exact) 
                        ? 'var(--color-accent-primary)' 
                        : 'transparent'
                    }}
                  >
                    <section.icon className="h-5 w-5 mr-3" />
                    {section.name}
                  </Link>
                ) : (
                  // 分组
                  <div>
                    <h3 
                      className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--color-text-secondary)' }}
                    >
                      {section.name}
                    </h3>
                    <div className="space-y-1">
                      {section.items.map((item, itemIdx) => (
                        <Link
                          key={itemIdx}
                          to={item.path}
                          onClick={onClose}
                          className={`
                            flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors
                            ${isActive(item.path) 
                              ? 'bg-opacity-10' 
                              : 'hover:bg-opacity-5'
                            }
                          `}
                          style={{
                            color: isActive(item.path) 
                              ? 'var(--color-accent-primary)' 
                              : 'var(--color-text-primary)',
                            backgroundColor: isActive(item.path) 
                              ? 'var(--color-accent-primary)' 
                              : 'transparent'
                          }}
                        >
                          <item.icon className="h-5 w-5 mr-3" />
                          {item.name}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </nav>

          {/* 底部信息 */}
          <div 
            className="p-4 border-t text-xs text-center"
            style={{ 
              borderColor: 'var(--color-border-primary)',
              color: 'var(--color-text-secondary)'
            }}
          >
            版本 1.0.1
          </div>
        </div>
      </aside>
    </>
  );
}

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      {/* 侧边栏 */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <header 
          className="flex items-center justify-between px-4 py-3 border-b"
          style={{ 
            backgroundColor: 'var(--color-bg-secondary)',
            borderColor: 'var(--color-border-primary)'
          }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-md hover:bg-opacity-10"
            style={{ color: 'var(--color-text-primary)' }}
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
          
          <div className="flex-1" />
          
          <ThemeToggle />
        </header>

        {/* 页面内容 */}
        <main className="flex-1 overflow-y-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/instances" element={<Instances />} />
            <Route path="/accounts" element={<Accounts />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/positions" element={<Positions />} />
            <Route path="/fund-manager" element={<FundManager />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/settings/theme" element={<ThemeSettings />} />
            <Route path="/symbols" element={<Symbols />} />
            <Route path="/system" element={<System />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <Router>
        <AppContent />
      </Router>
    </ThemeProvider>
  );
}

export default App;
