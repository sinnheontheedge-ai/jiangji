// 主题工具函数和预设主题

// 预设主题配置
export const PRESET_THEMES = {
  light: {
    name: '浅色主题',
    mode: 'light',
    colors: {
      background: {
        primary: '#FFFFFF',
        secondary: '#F9FAFB',
        tertiary: '#F3F4F6',
        modal: '#FFFFFF',
      },
      text: {
        primary: '#111827',
        secondary: '#6B7280',
        tertiary: '#9CA3AF',
        inverse: '#FFFFFF',
      },
      accent: {
        primary: '#4F46E5',
        success: '#10B981',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#3B82F6',
      },
      border: {
        primary: '#E5E7EB',
        secondary: '#D1D5DB',
      },
      interactive: {
        hover: '#EEF2FF',
        active: '#E0E7FF',
        focus: '#4F46E5',
      },
    },
  },
  
  dark: {
    name: '深色主题',
    mode: 'dark',
    colors: {
      background: {
        primary: '#111827',
        secondary: '#1F2937',
        tertiary: '#374151',
        modal: '#1F2937',
      },
      text: {
        primary: '#F9FAFB',
        secondary: '#D1D5DB',
        tertiary: '#9CA3AF',
        inverse: '#111827',
      },
      accent: {
        primary: '#6366F1',
        success: '#34D399',
        warning: '#FBBF24',
        error: '#F87171',
        info: '#60A5FA',
      },
      border: {
        primary: '#374151',
        secondary: '#4B5563',
      },
      interactive: {
        hover: '#374151',
        active: '#4B5563',
        focus: '#6366F1',
      },
    },
  },
  
  highContrast: {
    name: '高对比度',
    mode: 'high-contrast',
    colors: {
      background: {
        primary: '#FFFFFF',
        secondary: '#F3F4F6',
        tertiary: '#E5E7EB',
        modal: '#FFFFFF',
      },
      text: {
        primary: '#000000',
        secondary: '#374151',
        tertiary: '#6B7280',
        inverse: '#FFFFFF',
      },
      accent: {
        primary: '#3730A3',
        success: '#047857',
        warning: '#B45309',
        error: '#B91C1C',
        info: '#1E40AF',
      },
      border: {
        primary: '#D1D5DB',
        secondary: '#9CA3AF',
      },
      interactive: {
        hover: '#E5E7EB',
        active: '#D1D5DB',
        focus: '#3730A3',
      },
    },
  },
  
  trading: {
    name: '交易主题',
    mode: 'trading',
    colors: {
      background: {
        primary: '#0F1419',
        secondary: '#1C2127',
        tertiary: '#2D333B',
        modal: '#1C2127',
      },
      text: {
        primary: '#E6EDF3',
        secondary: '#8B949E',
        tertiary: '#6E7681',
        inverse: '#0F1419',
      },
      accent: {
        primary: '#58A6FF',
        success: '#3FB950',
        warning: '#D29922',
        error: '#F85149',
        info: '#58A6FF',
      },
      border: {
        primary: '#30363D',
        secondary: '#21262D',
      },
      interactive: {
        hover: '#30363D',
        active: '#21262D',
        focus: '#58A6FF',
      },
    },
  },
};

// 应用主题到CSS变量
export const applyTheme = (theme) => {
  const root = document.documentElement;
  
  // 背景色
  root.style.setProperty('--color-bg-primary', theme.colors.background.primary);
  root.style.setProperty('--color-bg-secondary', theme.colors.background.secondary);
  root.style.setProperty('--color-bg-tertiary', theme.colors.background.tertiary);
  root.style.setProperty('--color-bg-modal', theme.colors.background.modal);
  
  // 文字颜色
  root.style.setProperty('--color-text-primary', theme.colors.text.primary);
  root.style.setProperty('--color-text-secondary', theme.colors.text.secondary);
  root.style.setProperty('--color-text-tertiary', theme.colors.text.tertiary);
  root.style.setProperty('--color-text-inverse', theme.colors.text.inverse);
  
  // 强调色
  root.style.setProperty('--color-accent-primary', theme.colors.accent.primary);
  root.style.setProperty('--color-accent-success', theme.colors.accent.success);
  root.style.setProperty('--color-accent-warning', theme.colors.accent.warning);
  root.style.setProperty('--color-accent-error', theme.colors.accent.error);
  root.style.setProperty('--color-accent-info', theme.colors.accent.info);
  
  // 边框
  root.style.setProperty('--color-border-primary', theme.colors.border.primary);
  root.style.setProperty('--color-border-secondary', theme.colors.border.secondary);
  
  // 交互状态
  root.style.setProperty('--color-interactive-hover', theme.colors.interactive.hover);
  root.style.setProperty('--color-interactive-active', theme.colors.interactive.active);
  root.style.setProperty('--color-interactive-focus', theme.colors.interactive.focus);
};

// 从localStorage加载主题
export const loadTheme = () => {
  try {
    const savedTheme = localStorage.getItem('theme-config');
    if (savedTheme) {
      return JSON.parse(savedTheme);
    }
  } catch (error) {
    console.error('加载主题失败:', error);
  }
  return PRESET_THEMES.light; // 默认浅色主题
};

// 保存主题到localStorage
export const saveTheme = (theme) => {
  try {
    localStorage.setItem('theme-config', JSON.stringify(theme));
  } catch (error) {
    console.error('保存主题失败:', error);
  }
};

// 导出主题配置
export const exportTheme = (theme) => {
  const dataStr = JSON.stringify(theme, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(dataBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `theme-${Date.now()}.json`;
  link.click();
  URL.revokeObjectURL(url);
};

// 导入主题配置
export const importTheme = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const theme = JSON.parse(e.target.result);
        resolve(theme);
      } catch (error) {
        reject(new Error('无效的主题配置文件'));
      }
    };
    reader.onerror = () => reject(new Error('读取文件失败'));
    reader.readAsText(file);
  });
};

// 生成渐变色
export const generateGradient = (color1, color2, angle = 135) => {
  return `linear-gradient(${angle}deg, ${color1}, ${color2})`;
};

// 颜色亮度调整
export const adjustBrightness = (color, amount) => {
  const hex = color.replace('#', '');
  const r = Math.max(0, Math.min(255, parseInt(hex.substring(0, 2), 16) + amount));
  const g = Math.max(0, Math.min(255, parseInt(hex.substring(2, 4), 16) + amount));
  const b = Math.max(0, Math.min(255, parseInt(hex.substring(4, 6), 16) + amount));
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
};

// 颜色透明度
export const addAlpha = (color, alpha) => {
  const hex = color.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};
