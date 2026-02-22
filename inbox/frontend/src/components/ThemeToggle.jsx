import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { SunIcon, MoonIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { useNavigate } from 'react-router-dom';

export default function ThemeToggle() {
  const { theme, applyPreset } = useTheme();
  const [showMenu, setShowMenu] = useState(false);
  const navigate = useNavigate();

  const isDark = theme.mode === 'dark' || theme.mode === 'trading';

  const quickToggle = () => {
    if (isDark) {
      applyPreset('light');
    } else {
      applyPreset('dark');
    }
  };

  return (
    <div className="relative">
      {/* 快速切换按钮 */}
      <button
        onClick={quickToggle}
        className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title={isDark ? '切换到浅色主题' : '切换到深色主题'}
      >
        {isDark ? (
          <SunIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
        ) : (
          <MoonIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
        )}
      </button>

      {/* 设置按钮 */}
      <button
        onClick={() => navigate('/settings/theme')}
        className="ml-2 p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        title="主题设置"
      >
        <Cog6ToothIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
      </button>
    </div>
  );
}
