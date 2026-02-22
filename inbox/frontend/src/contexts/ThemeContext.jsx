import React, { createContext, useState, useEffect, useContext } from 'react';
import { PRESET_THEMES, applyTheme, loadTheme, saveTheme } from '../utils/themeUtils';

// 创建Context
const ThemeContext = createContext({
  theme: PRESET_THEMES.light,
  setTheme: () => {},
  applyPreset: () => {},
  updateColor: () => {},
  resetTheme: () => {},
  exportTheme: () => {},
  importTheme: () => {},
});

// Provider组件
export const ThemeProvider = ({ children }) => {
  const [theme, setThemeState] = useState(PRESET_THEMES.light);
  const [isCustom, setIsCustom] = useState(false);

  // 初始化:从localStorage加载主题
  useEffect(() => {
    const savedTheme = loadTheme();
    setThemeState(savedTheme);
    applyTheme(savedTheme);
    
    // 检查是否为自定义主题
    const isPreset = Object.values(PRESET_THEMES).some(
      preset => JSON.stringify(preset) === JSON.stringify(savedTheme)
    );
    setIsCustom(!isPreset);
  }, []);

  // 设置主题
  const setTheme = (newTheme) => {
    setThemeState(newTheme);
    applyTheme(newTheme);
    saveTheme(newTheme);
    
    // 检查是否为自定义主题
    const isPreset = Object.values(PRESET_THEMES).some(
      preset => JSON.stringify(preset) === JSON.stringify(newTheme)
    );
    setIsCustom(!isPreset);
  };

  // 应用预设主题
  const applyPreset = (presetName) => {
    const preset = PRESET_THEMES[presetName];
    if (preset) {
      setTheme(preset);
    }
  };

  // 更新单个颜色
  const updateColor = (path, value) => {
    const newTheme = { ...theme };
    const keys = path.split('.');
    let current = newTheme.colors;
    
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    
    current[keys[keys.length - 1]] = value;
    setTheme(newTheme);
  };

  // 重置为默认主题
  const resetTheme = () => {
    setTheme(PRESET_THEMES.light);
  };

  // 导出主题
  const exportThemeConfig = () => {
    const dataStr = JSON.stringify(theme, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `theme-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // 导入主题
  const importThemeConfig = async (file) => {
    try {
      const text = await file.text();
      const importedTheme = JSON.parse(text);
      setTheme(importedTheme);
      return true;
    } catch (error) {
      console.error('导入主题失败:', error);
      return false;
    }
  };

  const value = {
    theme,
    isCustom,
    setTheme,
    applyPreset,
    updateColor,
    resetTheme,
    exportTheme: exportThemeConfig,
    importTheme: importThemeConfig,
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

// 自定义Hook
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export default ThemeContext;
