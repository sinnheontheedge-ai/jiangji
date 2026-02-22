import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  DocumentTextIcon,
  UserGroupIcon,
  CogIcon,
  ShoppingCartIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  BellIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import ThemeToggle from './ThemeToggle';

const navigation = [
  { name: '仪表盘', href: '/dashboard', icon: HomeIcon },
  { name: '策略管理', href: '/strategies', icon: DocumentTextIcon },
  { name: '账户管理', href: '/accounts', icon: UserGroupIcon },
  { name: '资金管理', href: '/fund-manager', icon: CurrencyDollarIcon },
  { name: '实例管理', href: '/instances', icon: CogIcon },
  { name: '订单记录', href: '/orders', icon: ShoppingCartIcon },
  { name: '持仓管理', href: '/positions', icon: ChartBarIcon },
  { name: '通知配置', href: '/notifications', icon: BellIcon },
  { name: '系统设置', href: '/settings', icon: Cog6ToothIcon },
];

export default function Layout() {
  const location = useLocation();

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      {/* 侧边栏 */}
      <div 
        className="fixed inset-y-0 left-0 w-64 border-r" 
        style={{ 
          backgroundColor: 'var(--color-bg-secondary)',
          borderColor: 'var(--color-border-primary)'
        }}
      >
        {/* Logo */}
        <div 
          className="flex items-center justify-center h-16 border-b" 
          style={{ borderColor: 'var(--color-border-primary)' }}
        >
          <h1 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
            交易机器人
          </h1>
        </div>

        {/* 导航菜单 */}
        <nav className="mt-5 px-2 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className="group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-colors"
                style={{
                  backgroundColor: isActive ? 'var(--color-interactive-active)' : 'transparent',
                  color: isActive ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)';
                    e.currentTarget.style.color = 'var(--color-text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--color-text-secondary)';
                  }
                }}
              >
                <item.icon
                  className="mr-3 flex-shrink-0 h-6 w-6"
                  style={{
                    color: isActive ? 'var(--color-accent-primary)' : 'var(--color-text-tertiary)'
                  }}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* 主内容区 */}
      <div className="pl-64">
        {/* 顶部栏 */}
        <div 
          className="sticky top-0 z-10 flex h-16 flex-shrink-0 border-b" 
          style={{ 
            backgroundColor: 'var(--color-bg-secondary)',
            borderColor: 'var(--color-border-primary)'
          }}
        >
          <div className="flex flex-1 justify-between px-4">
            <div className="flex flex-1 items-center">
              <h2 className="text-lg font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {navigation.find((item) => item.href === location.pathname)?.name || '交易机器人'}
              </h2>
            </div>
            <div className="ml-4 flex items-center space-x-4">
              {/* 主题切换按钮 */}
              <ThemeToggle />
              
              {/* 系统状态 */}
              <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                系统运行中
              </span>
              <div className="h-2 w-2 rounded-full" style={{ backgroundColor: 'var(--color-accent-success)' }}></div>
            </div>
          </div>
        </div>

        {/* 页面内容 */}
        <main className="flex-1">
          <div className="py-6">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 md:px-8">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
